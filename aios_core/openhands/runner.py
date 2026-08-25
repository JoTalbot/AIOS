"""Оркестратор OpenHands-контура (F5): lifecycle задачи от PENDING до PR.

Поток (план, Этап 12): PLANNING (Architect) → READY → RUNNING (Coder) →
TESTING (Tester) → REVIEW (Reviewer) → [SECURITY_REVIEW/QA — только если
объявлены в required_gates] → ветка + diff-проверка прав + PR → COMPLETED.

Связность обеспечивается существующими механизмами:
- переходы — ``state_machine.transition`` (гейты и retry-лимит там);
- аудит — ``audit.OHAuditLogger`` (маскирование секретов там);
- права — ``permissions.check_paths`` (protected/allowed/deny);
- Cloud — ``client.OpenHandsClient``; git/PR — ``github.GitHubHelper``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from aios_core.orchestrator import TaskStatus

from .audit import OHAuditLogger
from .github import GitHubHelper
from .models import (
    AgentRole,
    FailureReport,
    Gate,
    ReviewDecision,
    TaskExtras,
)
from .permissions import check_paths
from .profiles import build_prompt, conversation_title
from .state_machine import OHStatus, TransitionError, transition
from .verdicts import parse_review_verdict


class ConversationClient(Protocol):
    """Минимальный контракт Cloud-клиента для оркестратора."""

    def start_conversation(
        self,
        prompt: str,
        *,
        repository: str | None = None,
        branch: str | None = None,
        title: str | None = None,
        run: bool = True,
    ) -> dict: ...

    def wait_start_task(self, start_task_id: str, **kwargs) -> dict: ...

    def wait_execution(self, conversation_id: str, **kwargs) -> str: ...

    def events_search(self, conversation_id: str, *, limit: int = 100) -> dict: ...

    def conversation_url(self, conversation_id: str) -> str: ...


@dataclass
class RunResult:
    """Итог прогона оркестратора."""

    status: str
    extras: TaskExtras
    report: FailureReport | None = None
    pr_url: str | None = None
    error: str | None = None


# Маршрутизация линейных стадий: (текущий статус, роль разговора или None,
# следующий статус). Маршрут после TESTING зависит от required_gates (см. _stage_of).
_MVP_STAGES: tuple[tuple[str, AgentRole | None, str], ...] = (
    (TaskStatus.PLANNING, AgentRole.ARCHITECT, OHStatus.READY),
    (OHStatus.READY, None, TaskStatus.RUNNING),
    (TaskStatus.RUNNING, AgentRole.CODER, OHStatus.TESTING),
    (OHStatus.QA, AgentRole.QA, TaskStatus.COMPLETED),
)


class OHOrchestrator:
    """Runner MVP-потока для одной задачи.

    Args:
        client: Cloud-клиент (реальный ``OpenHandsClient`` или совместимый).
        github: GitHub-helper (ветки/PR) или None — тогда PR-стадия пропускается.
        audit: аудит-логгер контура.
        repository: ``owner/repo`` для Cloud-разговоров.
        base_branch: базовая ветка для diff/PR.
    """

    def __init__(
        self,
        client: ConversationClient,
        github: GitHubHelper | None = None,
        audit: OHAuditLogger | None = None,
        repository: str | None = None,
        base_branch: str = "main",
    ) -> None:
        self._client = client
        self._github = github
        self._audit = audit or OHAuditLogger()
        self._repository = repository
        self._base = base_branch

    # ── публичный API ─────────────────────────────────────────────

    def run(self, task_id: str, title: str, description: str, extras: TaskExtras | None = None) -> RunResult:
        """Выполнить полный MVP-lifecycle задачи (с retry по state machine)."""
        extras = extras or TaskExtras(task_id=task_id)
        branch = extras.branch or f"agent/oh-{task_id}"
        status: str = TaskStatus.PENDING
        last_error: str | None = None

        while status not in (TaskStatus.COMPLETED, TaskStatus.CANCELLED):
            try:
                status = self._step(status, task_id, title, description, extras, branch)
            except Exception as exc:
                last_error = str(exc)
                extras.error = last_error
                self._audit.log("stage_error", task_id, AgentRole.ORCHESTRATOR, stage=status, error=last_error)
                if status in (TaskStatus.PLANNING, TaskStatus.RUNNING, OHStatus.TESTING, OHStatus.QA):
                    # Гейт-нарушение — баг маршрута контура, не retry.
                    if isinstance(exc, TransitionError) and "COMPLETED запрещён" in last_error:
                        raise
                    status = self._move(status, TaskStatus.FAILED, task_id, extras)
                elif status in (OHStatus.REVIEW, OHStatus.SECURITY_REVIEW):
                    status = self._move(status, OHStatus.BLOCKED, task_id, extras)
                else:
                    raise

        report = None
        if status != TaskStatus.COMPLETED:
            report = FailureReport(
                task_id=task_id,
                reason="retry limit exhausted" if extras.retry_count >= extras.max_retries else "task not completed",
                attempts=extras.retry_count + 1,
                last_error=last_error or extras.error,
                files_changed=tuple(self._safe_changed_files(branch)),
                suggested_next_step="разобрать отчёт и завести задачу вручную",
            )
            self._audit.log_decision(task_id, AgentRole.ORCHESTRATOR, "failed", reason=report.reason)
        return RunResult(status=status, extras=extras, report=report, error=last_error)

    # ── шаги ──────────────────────────────────────────────────────

    def _step(
        self,
        status: str,
        task_id: str,
        title: str,
        description: str,
        extras: TaskExtras,
        branch: str,
    ) -> str:
        if status == TaskStatus.PENDING:
            return self._move(status, TaskStatus.PLANNING, task_id, extras)
        if status in (TaskStatus.FAILED, OHStatus.BLOCKED):
            # Retry засчитывает state machine; лимит исчерпан → CANCELLED.
            if not extras.can_retry():
                return self._move(status, TaskStatus.CANCELLED, task_id, extras)
            return self._move(status, TaskStatus.PLANNING, task_id, extras)

        stage = self._stage_of(status, extras)
        if stage is None:
            raise RuntimeError(f"неизвестный статус стадии: {status}")

        role, next_status = stage
        if role is not None:
            decision = self._run_stage(task_id, role, title, description, extras, branch)
            if role == AgentRole.REVIEWER and decision == ReviewDecision.CHANGES_REQUESTED:
                self._audit.log_decision(task_id, AgentRole.REVIEWER, decision)
                return self._move(status, OHStatus.BLOCKED, task_id, extras)
        else:
            self._audit.log("stage_skip_conversation", task_id, AgentRole.ORCHESTRATOR, stage=status)

        if next_status == TaskStatus.COMPLETED:
            self._finalize(task_id, title, description, extras, branch)
        return self._move(status, next_status, task_id, extras)

    def _stage_of(self, status: str, extras: TaskExtras) -> tuple[AgentRole | None, str] | None:
        """(роль, следующий статус) для текущего статуса с учётом required_gates.

        Маршрут после TESTING зависит от гейтов:
        - MVP (гейты tests+review): testing → review → completed;
        - +security: testing → review → security_review (→ qa) → completed;
        - только qa (без security): testing → qa → completed.
        """
        has_security = Gate.SECURITY_REVIEW in extras.required_gates
        has_qa = Gate.QA in extras.required_gates
        if status == OHStatus.TESTING:
            if has_security:
                return AgentRole.TESTER, OHStatus.REVIEW
            if has_qa:
                return AgentRole.TESTER, OHStatus.QA
            return AgentRole.TESTER, OHStatus.REVIEW
        if status == OHStatus.REVIEW:
            if has_security:
                return AgentRole.REVIEWER, OHStatus.SECURITY_REVIEW
            return AgentRole.REVIEWER, TaskStatus.COMPLETED
        if status == OHStatus.SECURITY_REVIEW:
            if has_qa:
                return AgentRole.SECURITY, OHStatus.QA
            return AgentRole.SECURITY, TaskStatus.COMPLETED
        mvp = {s: (role, nxt) for s, role, nxt in _MVP_STAGES}
        if status in mvp:
            return mvp[status]
        return None

    def _run_stage(
        self,
        task_id: str,
        role: AgentRole,
        title: str,
        description: str,
        extras: TaskExtras,
        branch: str,
    ) -> str | None:
        """Запустить разговор роли и дождаться исполнения."""
        context = f"Ветка: {branch}. Предыдущие разговоры: {extras.conversation_ids or 'нет'}."
        prompt = build_prompt(role, description, context=context)
        start = self._client.start_conversation(
            prompt,
            repository=self._repository,
            branch=branch,
            title=conversation_title(role, task_id),
        )
        start_task_id = start.get("id", "")
        conversation_id = start.get("app_conversation_id", "")
        if not conversation_id:
            task = self._client.wait_start_task(start_task_id)
            conversation_id = task.get("app_conversation_id", "")
        extras.conversation_ids[role.value] = conversation_id
        self._audit.log(
            "conversation_started",
            task_id,
            role,
            conversation_id=conversation_id,
            url=self._client.conversation_url(conversation_id),
        )
        self._client.wait_execution(conversation_id)
        if role in (AgentRole.REVIEWER, AgentRole.SECURITY, AgentRole.QA):
            return self._verdict_of(task_id, role, conversation_id)
        return None

    def _verdict_of(self, task_id: str, role: AgentRole, conversation_id: str) -> str:
        """Вердикт роли из событий разговора; fallback APPROVED с аудитом."""
        try:
            payload = self._client.events_search(conversation_id)
        except Exception as exc:
            self._audit.log("verdict_fallback", task_id, role, reason=f"events: {exc}")
            return ReviewDecision.APPROVED
        verdict = parse_review_verdict(payload)
        if verdict is None:
            self._audit.log("verdict_fallback", task_id, role, reason="no token in events")
            return ReviewDecision.APPROVED
        self._audit.log_decision(task_id, role, verdict)
        return verdict

    def _finalize(self, task_id: str, title: str, description: str, extras: TaskExtras, branch: str) -> None:
        """Ветка, проверка diff по правам, PR — перед COMPLETED."""
        if self._github is None:
            self._audit.log("finalize_skipped", task_id, AgentRole.ORCHESTRATOR, reason="no github helper")
            return
        changed = self._github.changed_files(self._base)
        allowed, denied = check_paths(AgentRole.CODER, changed)
        self._audit.log(
            "diff_checked", task_id, AgentRole.ORCHESTRATOR, allowed=len(allowed), denied=denied
        )
        if denied:
            raise RuntimeError(f"diff содержит запрещённые пути: {denied}")
        if changed:
            self._github.push_branch(branch)
            pr = self._github.create_pull_request(
                branch=branch,
                title=f"oh({task_id}): {title}",
                body=description,
                base=self._base,
                draft=True,
            )
            extras.artifacts = (*extras.artifacts, pr.get("html_url", ""))
            self._audit.log("pr_created", task_id, AgentRole.ORCHESTRATOR, url=pr.get("html_url", ""))

    def _move(self, src: str, dst: str, task_id: str, extras: TaskExtras) -> str:
        """Переход через state machine с аудитом."""
        new_status = transition(src, dst, extras)
        self._audit.log_transition(task_id, AgentRole.ORCHESTRATOR, src, new_status)
        return new_status

    def _safe_changed_files(self, branch: str) -> list[str]:
        if self._github is None:
            return []
        try:
            return self._github.changed_files(self._base)
        except Exception:
            return []
