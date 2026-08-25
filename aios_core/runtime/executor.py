"""Common executor lifecycle and policy boundary for AIOS agents."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .contracts import AgentResult, AgentStatus, AgentTask
from .events import EventBus
from .policy import PolicyDecision, PolicyEngine


class AgentHandler(Protocol):
    def __call__(self, task: AgentTask) -> AgentResult: ...


@dataclass(frozen=True)
class ExecutionRecord:
    task_id: str
    status: AgentStatus
    result: AgentResult


class AgentExecutor:
    """Run an agent through one deterministic lifecycle and policy boundary."""

    def __init__(self, handler: AgentHandler, *, event_bus: EventBus | None = None, policy: PolicyEngine | None = None) -> None:
        self.handler = handler
        self.event_bus = event_bus
        self.policy = policy

    def _emit(self, name: str, task_id: str, **payload: object) -> None:
        if self.event_bus is not None:
            self.event_bus.publish(name, task_id, **payload)

    def authorize(self, task: AgentTask, permission: str) -> PolicyDecision:
        if self.policy is None:
            return PolicyDecision.ALLOW
        result = self.policy.check(task, permission)
        self._emit("POLICY_CHECKED", task.task_id, permission=permission, decision=result.decision.value, reason=result.reason)
        return result.decision

    def execute(self, task: AgentTask, *, required_permission: str | None = None) -> ExecutionRecord:
        if task.status not in {AgentStatus.CREATED, AgentStatus.QUEUED}:
            self._emit("AGENT_BLOCKED", task.task_id, reason="invalid_initial_status", status=task.status.value)
            raise ValueError(f"task {task.task_id} is not executable from {task.status}")

        if required_permission is not None:
            decision = self.authorize(task, required_permission)
            if decision is not PolicyDecision.ALLOW:
                self._emit("AGENT_BLOCKED", task.task_id, reason=decision.value, permission=required_permission)
                return ExecutionRecord(
                    task.task_id,
                    AgentStatus.BLOCKED,
                    AgentResult(
                        task_id=task.task_id,
                        status=AgentStatus.BLOCKED,
                        errors=(f"policy decision: {decision.value}",),
                        verdict="BLOCKED",
                    ),
                )

        running = task.with_status(AgentStatus.RUNNING)
        self._emit("AGENT_STARTED", running.task_id, status=running.status.value)
        try:
            result = self.handler(running)
        except Exception as exc:
            result = AgentResult(
                task_id=running.task_id,
                status=AgentStatus.FAILED,
                output="",
                errors=(f"{type(exc).__name__}: {exc}",),
            )

        final_status = result.status
        if final_status not in {AgentStatus.COMPLETED, AgentStatus.FAILED, AgentStatus.BLOCKED}:
            final_status = AgentStatus.FAILED
            result = AgentResult(
                task_id=running.task_id,
                status=final_status,
                output=result.output,
                evidence=result.evidence,
                artifacts=result.artifacts,
                tests=result.tests,
                risks=result.risks,
                errors=(*result.errors, "handler returned non-terminal status"),
                cost=result.cost,
                duration_ms=result.duration_ms,
                verdict=result.verdict,
            )

        event_name = {
            AgentStatus.COMPLETED: "AGENT_COMPLETED",
            AgentStatus.FAILED: "AGENT_FAILED",
            AgentStatus.BLOCKED: "AGENT_BLOCKED",
        }[final_status]
        self._emit(event_name, running.task_id, status=final_status.value, verdict=result.verdict)
        return ExecutionRecord(running.task_id, final_status, result)
