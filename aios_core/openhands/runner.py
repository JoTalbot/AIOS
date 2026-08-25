"""Оркестратор OpenHands-контура AIOS с bounded repair loop, memory и specialist review."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from aios_core.orchestrator import TaskStatus
from .agent_score import AgentScoreboard
from .audit import OHAuditLogger
from .policy_resolver import resolve_ci_policy
from .ci_provenance import CIProvenanceCollector
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
from .specialist_spawner import SpecialistSpawner
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
    (TaskStatus.QA, AgentRole.QA, TaskStatus.COMPLETED),
)


class OHOrchestrator:
    """Lifecycle runner: plan → code → test → review → specialist review → CI → gates → PR."""

    def __init__(self, client: ConversationClient, github: GitHubHelper | None = None, audit: OHAuditLogger | None = None, repository: str | None = None, base_branch: str = "main", scoreboard: AgentScoreboard | None = None, evidence_gate: EvidenceGate | None = None, ci_provenance: CIProvenanceCollector | None = None) -> None:
        self._client = client
        self._github = github
        self._audit = audit or OHAuditLogger()
        self._repository = repository
        self._base = base_branch
        self.scoreboard = scoreboard or AgentScoreboard()
        self._evidence_gate = evidence_gate or EvidenceGate()
        self._ci_provenance = ci_provenance
        self._specialist_spawner = SpecialistSpawner(client, repository=repository)

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
            return self._run_security_review_stage(task_id, title, description, extras, branch, memory)
        if status == OHStatus.QA:
            self._finalize(task_id, title, description, extras, branch)
            return TaskStatus.COMPLETED
        raise TransitionError(f"неизвестный OpenHands status: {status}")

    def _run_security_review_stage(self, task_id: str, title: str, description: str, extras: TaskExtras, branch: str, memory: TaskMemory) -> str:
        changed = self._github.changed_files(self._base) if self._github is not None else []
        policy = resolve_ci_policy(description, changed)
        self._audit.log("security_policy_checked", task_id, AgentRole.ORCHESTRATOR, security_forced=policy.security_forced, reasons=policy.reasons)
        conversation_id = extras.conversation_ids.get(AgentRole.SECURITY.value, "")
        if policy.security_forced and not conversation_id:
            if self._github is None:
                raise TransitionError("security review required: GitHub helper unavailable for specialist spawn")
            spawned = self._specialist_spawner.spawn(role=AgentRole.SECURITY.value, task_id=task_id, title=title, description=description, changed_files=changed, branch=branch, reasons=policy.reasons)
            conversation_id = spawned.conversation_id
            extras.conversation_ids[AgentRole.SECURITY.value] = conversation_id
            self._audit.log("security_specialist_spawned", task_id, AgentRole.ORCHESTRATOR, conversation_id=conversation_id, reasons=policy.reasons)
        return self._run_review_stage(task_id, title, description, extras, branch, memory, AgentRole.SECURITY, OHStatus.QA)

    def _audit_gate_identity(self, task_id: str, role: AgentRole, action: str, *, decision: str | None = None, branch: str | None = None) -> None:
        fields: dict[str, object] = {"decision": decision} if decision is not None else {}
        if self._github is not None and branch is not None:
            try:
                fields["commit_sha"] = self._github.head_sha()
                fields["diff_hash"] = self._github.diff_hash(self._base)
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

    def _gate_identity_for(self, role: AgentRole, task_id: str) -> tuple[str | None, str | None]:
        for event in reversed(self._audit.chain.events):
            payload = event.payload
            if payload.get("type") == "openhands.gate_pass" and payload.get("agent") == role.value and payload.get("task_id") == task_id:
                return payload.get("commit_sha"), payload.get("diff_hash")
        return None, None

    def _evidence_context(self, task_id: str, extras: TaskExtras, branch: str) -> dict[str, object]:
        context: dict[str, object] = {"tests": Gate.TESTS in extras.passed_gates, "reviewer": ReviewDecision.APPROVED.value if Gate.REVIEW in extras.passed_gates else None, "security": ReviewDecision.APPROVED.value if Gate.SECURITY_REVIEW in extras.passed_gates else None, "audit_chain": self._audit.verify_chain()}
        if self._github is not None:
            try:
                context["commit_sha"] = self._github.head_sha()
                context["diff_hash"] = self._github.diff_hash(self._base)
                context["changed_files"] = self._github.changed_files(self._base)
            except Exception:
                pass
        test_commit, test_diff = self._gate_identity_for(AgentRole.TESTER, task_id)
        context["test_commit_sha"] = test_commit
        context["test_diff_hash"] = test_diff
        context["evidence_commit_sha"] = context.get("commit_sha")
        context["evidence_diff_hash"] = context.get("diff_hash")