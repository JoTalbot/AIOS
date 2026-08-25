"""Оркестратор OpenHands-контура AIOS с bounded repair loop, memory и specialist review."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from aios_core.orchestrator import TaskStatus
from .agent_score import AgentScoreboard
from .audit import OHAuditLogger
from .event_evidence import build_completion_report
from .gates import apply_gate, can_advance
from .github import GitHubHelper
from .handoff import AgentHandoff
from .memory import AgentMemoryEntry, TaskMemory
from .models import AgentRole, FailureReport, Gate, ReviewDecision, TaskExtras
from .permissions import check_paths
from .profiles import build_prompt, conversation_title
from .prompt_optimizer import PromptOptimizationSuggestion, suggest_improvements
from .specialist_pipeline import SpecialistResult, SpecialistReviewPipeline
from .state_machine import OHStatus, TransitionError, transition
from .task_profiles import classify_task
from .verdicts import parse_review_verdict


class ConversationClient(Protocol):
    def start_conversation(self, prompt: str, *, repository: str | None = None, branch: str | None = None, title: str | None = None, run: bool = True) -> dict: ...
    def wait_start_task(self, start_task_id: str, **kwargs) -> dict: ...
    def wait_execution(self, conversation_id: str, **kwargs) -> str: ...
    def events_search(self, conversation_id: str, *, limit: int = 100) -> dict: ...
    def conversation_url(self, conversation_id: str) -> str: ...


@dataclass
class RunResult:
    status: str
    extras: TaskExtras
    report: FailureReport | None = None
    pr_url: str | None = None
    error: str | None = None
    scoreboard: AgentScoreboard | None = None
    prompt_suggestions: tuple[PromptOptimizationSuggestion, ...] = ()


_MVP_STAGES: tuple[tuple[str, AgentRole | None, str], ...] = (
    (TaskStatus.PLANNING, AgentRole.ARCHITECT, OHStatus.READY),
    (OHStatus.READY, None, TaskStatus.RUNNING),
    (TaskStatus.RUNNING, AgentRole.CODER, OHStatus.TESTING),
    (OHStatus.QA, AgentRole.QA, TaskStatus.COMPLETED),
)


class OHOrchestrator:
    """Lifecycle runner: plan → code → test → review → specialist review → gates → PR."""

    def __init__(self, client: ConversationClient, github: GitHubHelper | None = None, audit: OHAuditLogger | None = None, repository: str | None = None, base_branch: str = "main", scoreboard: AgentScoreboard | None = None) -> None:
        self._client = client
        self._github = github
        self._audit = audit or OHAuditLogger()
        self._repository = repository
        self._base = base_branch
        self.scoreboard = scoreboard or AgentScoreboard()

    def run(self, task_id: str, title: str, description: str, extras: TaskExtras | None = None) -> RunResult:
        extras = extras or TaskExtras(task_id=task_id)
        branch = extras.branch or f"agent/oh-{task_id}"
        memory = TaskMemory(task_id)
        if self._github is not None:
            self._github.prepare_branch(branch, self._base)
        status: str = TaskStatus.PENDING
        last_error: str | None = None
        while status not in (TaskStatus.COMPLETED, TaskStatus.CANCELLED):
            try:
                status = self._step(status, task_id, title, description, extras, branch, memory)
            except Exception as exc:
                last_error = str(exc)
                extras.error = last_error
                self._audit.log("stage_error", task_id, AgentRole.ORCHESTRATOR, stage=status, error=last_error)
                if status in (TaskStatus.PLANNING, TaskStatus.RUNNING, OHStatus.TESTING, OHStatus.QA):
                    if isinstance(exc, TransitionError) and "COMPLETED запрещён" in last_error:
                        raise
                    status = self._move(status, TaskStatus.FAILED, task_id, extras)
                elif status in (OHStatus.REVIEW, OHStatus.SECURITY_REVIEW):
                    status = self._move(status, OHStatus.BLOCKED, task_id, extras)
                else:
                    raise
        suggestions = suggest_improvements(self.scoreboard)
        report = None
        if status != TaskStatus.COMPLETED:
            report = FailureReport(task_id=task_id, reason="repair/retry limit exhausted" if extras.retry_count >= extras.max_retries or extras.repair_count >= extras.max_repairs else "task not completed", attempts=extras.retry_count + extras.repair_count + 1, last_error=last_error or extras.error, files_changed=tuple(self._safe_changed_files(branch)), suggested_next_step="разобрать отчёт и завести задачу вручную")
            self._audit.log_decision(task_id, AgentRole.ORCHESTRATOR, "failed", reason=report.reason)
        return RunResult(status=status, extras=extras, report=report, error=last_error, scoreboard=self.scoreboard, prompt_suggestions=suggestions)

    def _step(self, status: str, task_id: str, title: str, description: str, extras: TaskExtras, branch: str, memory: TaskMemory) -> str:
        if status == TaskStatus.PENDING:
            return self._move(status, TaskStatus.PLANNING, task_id, extras)
        if status in (TaskStatus.FAILED, OHStatus.BLOCKED):
            if not extras.can_retry():
                return self._move(status, TaskStatus.CANCELLED, task_id, extras)
            return self._move(status, TaskStatus.PLANNING, task_id, extras)
        stage = self._stage_of(status, extras)
        if stage is None:
            raise RuntimeError(f"неизвестный статус стадии: {status}")
        role, next_status = stage
        if role is not None:
            decision = self._run_stage(task_id, role, description, extras, branch, memory)
            if role == AgentRole.REVIEWER and decision == ReviewDecision.CHANGES_REQUESTED:
                extras.review_decision = ReviewDecision.CHANGES_REQUESTED
                if not extras.can_repair():
                    raise TransitionError(f"лимит repair-итераций исчерпан ({extras.repair_count}/{extras.max_repairs})")
                extras.register_repair()
                return self._move(status, TaskStatus.RUNNING, task_id, extras)
            if role in (AgentRole.TESTER, AgentRole.REVIEWER, AgentRole.SECURITY, AgentRole.QA) and decision != ReviewDecision.APPROVED:
                raise TransitionError(f"{role.value}: gate не подтверждён, verdict={decision}")
            if role == AgentRole.REVIEWER:
                extras.review_decision = ReviewDecision.APPROVED
        else:
            self._audit.log("stage_skip_conversation", task_id, AgentRole.ORCHESTRATOR, stage=status)
        if next_status == TaskStatus.COMPLETED:
            self._finalize(task_id, title, description, extras, branch)
        return self._move(status, next_status, task_id, extras)

    def _stage_of(self, status: str, extras: TaskExtras) -> tuple[AgentRole | None, str] | None:
        has_security = Gate.SECURITY_REVIEW in extras.required_gates
        has_qa = Gate.QA in extras.required_gates
        if status == OHStatus.TESTING:
            return AgentRole.TESTER, OHStatus.REVIEW
        if status == OHStatus.REVIEW:
            return (AgentRole.REVIEWER, OHStatus.SECURITY_REVIEW) if has_security else (AgentRole.REVIEWER, TaskStatus.COMPLETED)
        if status == OHStatus.SECURITY_REVIEW:
            return (AgentRole.SECURITY, OHStatus.QA) if has_qa else (AgentRole.SECURITY, TaskStatus.COMPLETED)
        return {s: (role, nxt) for s, role, nxt in _MVP_STAGES}.get(status)

    def _run_specialists(self, task_id: str, description: str, branch: str, task_type: str, memory: TaskMemory) -> ReviewDecision:
        def executor(spec, context: str) -> SpecialistResult:
            prompt = build_prompt(spec.role, f"SPECIALIST REVIEW: {spec.name}\nPurpose: {spec.purpose}\n\nTask:\n{description}", context=context)
            start = self._client.start_conversation(prompt, repository=self._repository, branch=branch, title=conversation_title(spec.role, f"{task_id}-{spec.name}"))
            start_task_id = start.get("id", "")
            conversation_id = start.get("app_conversation_id", "")
            if not conversation_id:
                conversation_id = self._client.wait_start_task(start_task_id).get("app_conversation_id", "")
            if not conversation_id:
                return SpecialistResult(spec, ReviewDecision.CHANGES_REQUESTED, error="missing conversation_id")
            try:
                evidence = self._client.wait_execution(conversation_id)
                payload = self._client.events_search(conversation_id)
                verdict = parse_review_verdict(payload)
                if verdict is None:
                    return SpecialistResult(spec, ReviewDecision.CHANGES_REQUESTED, error="missing explicit verdict")
                return SpecialistResult(spec, verdict, str(evidence)[-1500:])
            except Exception as exc:
                return SpecialistResult(spec, ReviewDecision.CHANGES_REQUESTED, error=str(exc))

        context = memory.compact_context()
        results, meta = SpecialistReviewPipeline(executor).run(task_type, context)
        for result in results:
            memory.add(AgentMemoryEntry(role=f"micro:{result.spec.name}", summary=f"specialist verdict={result.verdict.value}", decisions=[result.verdict.value], evidence=[result.evidence[-1000:] if result.evidence else result.error or "no evidence"]))
            self._audit.log_decision(task_id, result.spec.role, result.verdict, specialist=result.spec.name, error=result.error)
            self.scoreboard.record(f"micro:{result.spec.name}", success=result.verdict == ReviewDecision.APPROVED, reviewer_rejected=result.verdict == ReviewDecision.CHANGES_REQUESTED)
        self._audit.log_decision(task_id, AgentRole.REVIEWER, meta.decision, specialist="meta-review", blockers=meta.blockers)
        return meta.decision

    def _run_stage(self, task_id: str, role: AgentRole, description: str, extras: TaskExtras, branch: str, memory: TaskMemory) -> ReviewDecision | None:
        memory_context = memory.compact_context()
        repair_context = memory.repair_context() if role == AgentRole.CODER else ""
        context_parts = [f"Ветка: {branch}.", f"Предыдущие разговоры: {extras.conversation_ids or 'нет'}."]
        if memory_context:
            context_parts.append(memory_context)
        if repair_context:
            context_parts.append("REPAIR FEEDBACK:\n" + repair_context)
        prompt = build_prompt(role, description, context="\n".join(context_parts))
        start = self._client.start_conversation(prompt, repository=self._repository, branch=branch, title=conversation_title(role, task_id))
        start_task_id = start.get("id", "")
        conversation_id = start.get("app_conversation_id", "")
        if not conversation_id:
            conversation_id = self._client.wait_start_task(start_task_id).get("app_conversation_id", "")
        if not conversation_id:
            raise RuntimeError(f"OpenHands не вернул conversation_id для роли {role.value}")
        extras.conversation_ids[role.value] = conversation_id
        self._audit.log("conversation_started", task_id, role, conversation_id=conversation_id, url=self._client.conversation_url(conversation_id))
        before_files = self._safe_changed_files(branch)
        execution_result = self._client.wait_execution(conversation_id)
        payload = self._client.events_search(conversation_id)
        report = build_completion_report(payload, role.value)
        verdict = self._verdict_of(task_id, role, conversation_id) if role in (AgentRole.REVIEWER, AgentRole.SECURITY, AgentRole.QA, AgentRole.TESTER) else None
        if verdict == ReviewDecision.APPROVED and role == AgentRole.REVIEWER:
            task_type = classify_task(description).value
            specialist_decision = self._run_specialists(task_id, description, branch, task_type, memory)
            if specialist_decision != ReviewDecision.APPROVED:
                verdict = ReviewDecision.CHANGES_REQUESTED
        after_files = self._safe_changed_files(branch)
        stage_files = tuple(sorted(set(after_files) - set(before_files)))
        evidence_text = execution_result if isinstance(execution_result, str) else str(execution_result)
        handoff = AgentHandoff(
            status="COMPLETED" if verdict in (None, ReviewDecision.APPROVED) else "CHANGES_REQUESTED",
            summary=f"Stage {role.value} completed; runtime evidence collected.",
            files_changed=stage_files,
            commands_run=tuple(e.command for e in report.evidence) or (f"OpenHands conversation {conversation_id}",),
            evidence=tuple(e.result for e in report.evidence) or ((evidence_text[-1500:] or ""),),
            next_action=f"Advance after {role.value}" if verdict == ReviewDecision.APPROVED else "Repair and rerun stage",
            verdict=verdict.value if verdict else None,
        )
        gate_result = apply_gate(role, handoff, extras, report, actual_files=stage_files)
        self._audit.log("gate_validation", task_id, role, decision=gate_result.decision.value, reasons=gate_result.reasons, files=stage_files)
        if not can_advance(gate_result):
            if verdict == ReviewDecision.APPROVED:
                raise TransitionError(f"{role.value}: quality gate blocked by evidence/DoD/git: {gate_result.reasons}")
            return verdict
        if verdict == ReviewDecision.APPROVED:
            gate = {AgentRole.TESTER: Gate.TESTS, AgentRole.REVIEWER: Gate.REVIEW, AgentRole.SECURITY: Gate.SECURITY_REVIEW, AgentRole.QA: Gate.QA}.get(role)
            if gate is not None:
                self._audit.log("gate_passed", task_id, role, gate=gate.value, missing=sorted(g.value for g in extras.missing_gates()))
        self.scoreboard.record(role.value, success=verdict in (None, ReviewDecision.APPROVED), iterations=extras.repair_count + 1, reviewer_rejected=role == AgentRole.REVIEWER and verdict == ReviewDecision.CHANGES_REQUESTED, security_violation=role == AgentRole.SECURITY and verdict == ReviewDecision.CHANGES_REQUESTED)
        memory.add(AgentMemoryEntry(role=role.value, summary=f"Завершена стадия {role.value}; verdict={verdict.value if verdict else 'n/a'}", decisions=[verdict.value] if verdict else [], evidence=[evidence_text[-1500:] or "conversation completed"]))
        return verdict

    def _verdict_of(self, task_id: str, role: AgentRole, conversation_id: str) -> ReviewDecision:
        try:
            payload = self._client.events_search(conversation_id)
        except Exception as exc:
            self._audit.log("verdict_error", task_id, role, reason=f"events: {exc}")
            raise RuntimeError(f"не удалось получить verdict {role.value}: {exc}") from exc
        verdict = parse_review_verdict(payload)
        if verdict is None:
            self._audit.log("verdict_missing", task_id, role, reason="no explicit APPROVED/CHANGES_REQUESTED token")
            raise RuntimeError(f"{role.value}: отсутствует явный verdict; fail-closed")
        self._audit.log_decision(task_id, role, verdict)
        return verdict

    def _finalize(self, task_id: str, title: str, description: str, extras: TaskExtras, branch: str) -> None:
        if not extras.gates_satisfied():
            raise TransitionError(f"COMPLETED запрещён: не пройдены gates={sorted(g.value for g in extras.missing_gates())}")
        if self._github is None:
            self._audit.log("finalize_skipped", task_id, AgentRole.ORCHESTRATOR, reason="no github helper")
            return
        self._github.sync_branch(branch)
        changed = self._github.changed_files(self._base)
        allowed, denied = check_paths(AgentRole.CODER, changed)
        self._audit.log("diff_checked", task_id, AgentRole.ORCHESTRATOR, allowed=len(allowed), denied=denied)
        if denied:
            raise RuntimeError(f"diff содержит запрещённые пути: {denied}")
        if changed:
            self._github.push_branch(branch)
            pr = self._github.create_pull_request(branch=branch, title=f"oh({task_id}): {title}", body=description, base=self._base, draft=True)
            extras.artifacts = (*extras.artifacts, pr.get("html_url", ""))
            self._audit.log("pr_created", task_id, AgentRole.ORCHESTRATOR, url=pr.get("html_url", ""))

    def _move(self, src: str, dst: str, task_id: str, extras: TaskExtras) -> str:
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
