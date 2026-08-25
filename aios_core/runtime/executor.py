"""Common executor lifecycle for AIOS agents."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .contracts import AgentResult, AgentStatus, AgentTask


class AgentHandler(Protocol):
    def __call__(self, task: AgentTask) -> AgentResult: ...


@dataclass(frozen=True)
class ExecutionRecord:
    task_id: str
    status: AgentStatus
    result: AgentResult


class AgentExecutor:
    """Run an agent through one deterministic lifecycle boundary."""

    def __init__(self, handler: AgentHandler) -> None:
        self.handler = handler

    def execute(self, task: AgentTask) -> ExecutionRecord:
        if task.status not in {AgentStatus.CREATED, AgentStatus.QUEUED}:
            raise ValueError(f"task {task.task_id} is not executable from {task.status}")

        running = task.with_status(AgentStatus.RUNNING)
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
        if final_status not in {
            AgentStatus.COMPLETED,
            AgentStatus.FAILED,
            AgentStatus.BLOCKED,
        }:
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
        return ExecutionRecord(running.task_id, final_status, result)
