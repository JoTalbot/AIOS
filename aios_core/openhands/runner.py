"""Оркестратор OpenHands-контура AIOS с bounded repair loop, memory и specialist review."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from aios_core.orchestrator import TaskStatus
from .agent_score import AgentScoreboard
from .audit import OHAuditLogger
from .event_evidence import build_completion_report
from .evidence_gate import EvidenceGate
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

    def __init__(self, client: ConversationClient, github: GitHubHelper | None = None, audit: OHAuditLogger | None = None, repository: str | None = None, base_branch: str = "main", scoreboard: AgentScoreboard | None = None, evidence_gate: EvidenceGate | None = None) -> None:
        self._client = client
        self._github = github
        self._audit = audit or OHAuditLogger()
        self._repository = repository
        self._base = base_branch
        self.scoreboard = scoreboard or AgentScoreboard()
        self._evidence_gate = evidence_gate or EvidenceGate()

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
                        status = TaskStatus.BLOCKED
                    else:
                        status = TaskStatus.BLOCKED
                else:
                    status = TaskStatus.BLOCKED
        self._audit.log("task_completed" if status == TaskStatus.COMPLETED else "task_blocked", task_id, AgentRole.ORCHESTRATOR, status=status)
        return RunResult(status=status, extras=extras, error=last_error, scoreboard=self.scoreboard)

    def _step(self, status: str, task_id: str, title: str, description: str, extras: TaskExtras, branch: str, memory: TaskMemory) -> str:
        role = next((r for s, r, _ in _MVP_STAGES if s == status), AgentRole.ORCHESTRATOR)
        self._audit.log("stage_start", task_id, role or AgentRole.ORCHESTRATOR, status=status)
        if status == TaskStatus.PENDING:
            return TaskStatus.PLANNING
        if status == TaskStatus.PLANNING:
            return self._run_agent_stage(task_id, title, description, extras, branch, memory, AgentRole.ARCHITECT, OHStatus.READY)
        if status == OHStatus.READY:
            return TaskStatus.RUNNING
        if status == TaskStatus.RUNNING:
            return self._run_agent_stage(task_id, title, description, extras, branch, memory, AgentRole.CODER, OHStatus.TESTING)
        if status == OHStatus.TESTING:
            return self._run_review_stage(task_id, title, description, extras, branch, memory, AgentRole.TESTER, OHStatus.REVIEW)
        if status == OHStatus.REVIEW:
            return self._run_review_stage(task_id, title, description, extras, branch, memory, AgentRole.REVIEWER, OHStatus.SECURITY_REVIEW)
        if status == OHStatus.SECURITY_REVIEW:
            return self._run_review_stage(task_id, title, description, extras, branch, memory, AgentRole.SECURITY, OHStatus.QA)
        if status == OHStatus.QA:
            self._finalize(task_id, title, description, extras, branch)
            return TaskStatus.COMPLETED
        raise TransitionError(f"неизвестный OpenHands status: {status}")

    def _audit_gate_identity(self, task_id: str, role: AgentRole, action: str, *, decision: str | None = None, branch: str | None = None) -> None:
        fields: dict[str, object] = {"decision": decision} if decision is not None else {}
        if self._github is not None and branch is not None:
            try:
                fields["commit_sha"] = self._github.head_sha(branch)
                fields["diff_hash"] = self._github.diff_hash(self._base, branch)
            except Exception as exc:
                self._audit.log("git_identity_error", task_id, AgentRole.ORCHESTRATOR, action=action, error=str(exc))
                raise TransitionError(f"{action}: невозможно получить Git identity, gate заблокирован") from exc
        self._audit.log(action, task_id, role, branch=branch, **fields)

    def _run_agent_stage(self, task_id: str, title: str, description: str, extras: TaskExtras, branch: str, memory: TaskMemory, role: AgentRole, next_status: str) -> str:
        verdict = self._verdict_of(task_id, role, extras.conversation_ids.get(role.value, "")) if extras.conversation_ids.get(role.value) else None
        if verdict is not None:
            self._audit_gate_identity(task_id, role, "handoff", decision=verdict.value, branch=branch)
        return next_status

    def _run_review_stage(self, task_id: str, title: str, description: str, extras: TaskExtras, branch: str, memory: TaskMemory, role: AgentRole, next_status: str) -> str:
        verdict = self._verdict_of(task_id, role, extras.conversation_ids.get(role.value, "")) if extras.conversation_ids.get(role.value) else None
        if verdict is not None:
            action = "gate_pass" if verdict == ReviewDecision.APPROVED else "gate_block"
            self._audit_gate_identity(task_id, role, action, decision=verdict.value, branch=branch)
            if verdict == ReviewDecision.APPROVED:
                gate = {AgentRole.TESTER: Gate.TESTS, AgentRole.REVIEWER: Gate.REVIEW, AgentRole.SECURITY: Gate.SECURITY_REVIEW, AgentRole.QA: Gate.QA}.get(role)
                if gate is not None:
                    extras.mark_gate_passed(gate)
        return next_status

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

    def _evidence_context(self, task_id: str, extras: TaskExtras, branch: str) -> dict[str, object]:
        context: dict[str, object] = {"tests": Gate.TESTS in extras.passed_gates, "reviewer": ReviewDecision.APPROVED.value if Gate.REVIEW in extras.passed_gates else None, "security": ReviewDecision.APPROVED.value if Gate.SECURITY_REVIEW in extras.passed_gates else None, "audit_chain": self._audit.verify_chain()}
        if self._github is not None:
            try:
                context["commit_sha"] = self._github.head_sha(branch)
                context["diff_hash"] = self._github.diff_hash(self._base, branch)
                context["changed_files"] = self._github.changed_files(self._base)
            except Exception:
                pass
        context["audit_checkpoint"] = bool(self._audit.chain.checkpoints)
        return context

    def _finalize(self, task_id: str, title: str, description: str, extras: TaskExtras, branch: str) -> None:
        evidence = self._evidence_context(task_id, extras, branch)
        gate_result = self._evidence_gate.evaluate(extras, evidence)
        if not gate_result.allowed:
            self._audit.log("evidence_gate_block", task_id, AgentRole.ORCHESTRATOR, missing=gate_result.missing)
            raise TransitionError(f"COMPLETED запрещён: missing evidence={list(gate_result.missing)}")
        if self._github is None:
            raise TransitionError("COMPLETED запрещён: GitHub helper обязателен для evidence gate")
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