"""Common executor lifecycle, policy, approval and sandbox boundaries for AIOS agents."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .approval import ApprovalQueue, ApprovalStatus
from .contracts import AgentResult, AgentStatus, AgentTask
from .events import EventBus
from .policy import PolicyDecision, PolicyEngine
from .sandbox import SandboxExecutor


class AgentHandler(Protocol):
    def __call__(self, task: AgentTask) -> AgentResult: ...


@dataclass(frozen=True)
class ExecutionRecord:
    task_id: str
    status: AgentStatus
    result: AgentResult
    approval_request_id: str | None = None


class AgentExecutor:
    """Run an agent through deterministic policy, approval and sandbox boundaries."""

    def __init__(self, handler: AgentHandler, *, event_bus: EventBus | None = None, policy: PolicyEngine | None = None, approvals: ApprovalQueue | None = None, sandbox: SandboxExecutor | None = None) -> None:
        self.handler = handler
        self.event_bus = event_bus
        self.policy = policy
        self.approvals = approvals
        self.sandbox = sandbox

    def _emit(self, name: str, task_id: str, **payload: object) -> None:
        if self.event_bus is not None:
            self.event_bus.publish(name, task_id, **payload)

    def authorize(self, task: AgentTask, permission: str) -> PolicyDecision:
        if self.policy is None:
            return PolicyDecision.ALLOW
        result = self.policy.check(task, permission)
        self._emit("POLICY_CHECKED", task.task_id, permission=permission, decision=result.decision.value, reason=result.reason)
        return result.decision

    def execute(self, task: AgentTask, *, required_permission: str | None = None, approval_request_id: str | None = None) -> ExecutionRecord:
        if task.status not in {AgentStatus.CREATED, AgentStatus.QUEUED}:
            self._emit("AGENT_BLOCKED", task.task_id, reason="invalid_initial_status", status=task.status.value)
            raise ValueError(f"task {task.task_id} is not executable from {task.status}")

        decision = self.authorize(task, required_permission) if required_permission is not None else PolicyDecision.ALLOW
        if decision is PolicyDecision.APPROVAL_REQUIRED:
            if self.approvals is None:
                return self._blocked(task, "approval queue unavailable")
            if approval_request_id is None:
                request = self.approvals.request(task, required_permission, "policy requires explicit approval")
                self._emit("APPROVAL_REQUESTED", task.task_id, request_id=request.request_id, permission=required_permission)
                return ExecutionRecord(task.task_id, AgentStatus.BLOCKED, AgentResult(task.task_id, AgentStatus.BLOCKED, errors=("approval required",), verdict="PENDING_APPROVAL"), request.request_id)
            request = self.approvals.get(approval_request_id)
            if request.task_id != task.task_id or request.permission != required_permission or request.status is not ApprovalStatus.APPROVED:
                return self._blocked(task, "approval request is invalid or not approved", approval_request_id)
            self._emit("APPROVAL_GRANTED", task.task_id, request_id=approval_request_id, decided_by=request.decided_by)
        elif decision is PolicyDecision.DENY:
            return self._blocked(task, "policy decision: deny")
        elif decision is PolicyDecision.SANDBOX:
            if self.sandbox is None:
                return self._blocked(task, "sandbox executor unavailable")
            running = task.with_status(AgentStatus.RUNNING)
            self._emit("SANDBOX_STARTED", task.task_id)
            try:
                result = self.sandbox.execute(running)
            except Exception as exc:
                result = AgentResult(task.task_id, AgentStatus.FAILED, errors=(f"{type(exc).__name__}: {exc}",))
            self._emit("SANDBOX_FINISHED", task.task_id, status=result.status.value, verdict=result.verdict)
            return ExecutionRecord(task.task_id, result.status, result, approval_request_id)

        running = task.with_status(AgentStatus.RUNNING)
        self._emit("AGENT_STARTED", running.task_id, status=running.status.value)
        try:
            result = self.handler(running)
        except Exception as exc:
            result = AgentResult(task_id=running.task_id, status=AgentStatus.FAILED, errors=(f"{type(exc).__name__}: {exc}",))
        self._emit({AgentStatus.COMPLETED: "AGENT_COMPLETED", AgentStatus.FAILED: "AGENT_FAILED", AgentStatus.BLOCKED: "AGENT_BLOCKED"}.get(result.status, "AGENT_FAILED"), task.task_id, status=result.status.value, verdict=result.verdict)
        return ExecutionRecord(task.task_id, result.status, result, approval_request_id)

    def _blocked(self, task: AgentTask, reason: str, approval_request_id: str | None = None) -> ExecutionRecord:
        self._emit("AGENT_BLOCKED", task.task_id, reason=reason)
        return ExecutionRecord(task.task_id, AgentStatus.BLOCKED, AgentResult(task.task_id, AgentStatus.BLOCKED, errors=(reason,), verdict="BLOCKED"), approval_request_id)
