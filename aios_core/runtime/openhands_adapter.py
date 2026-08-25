"""Adapters that expose OpenHands through the common AIOS runtime contract."""
from __future__ import annotations

from typing import Any, Protocol

from .contracts import AgentResult, AgentStatus, AgentTask


class OpenHandsRunner(Protocol):
    def run(self, *, task: AgentTask) -> Any: ...


class OpenHandsAdapter:
    """Translate an OpenHands runner result into an AIOS AgentResult."""
    def __init__(self, runner: OpenHandsRunner) -> None:
        self.runner = runner

    def __call__(self, task: AgentTask) -> AgentResult:
        try:
            raw = self.runner.run(task=task)
        except Exception as exc:
            return AgentResult(task_id=task.task_id, status=AgentStatus.FAILED, errors=(f"{type(exc).__name__}: {exc}",))
        status = getattr(raw, "status", AgentStatus.COMPLETED)
        if isinstance(status, str):
            try:
                status = AgentStatus(status.lower())
            except ValueError:
                status = AgentStatus.FAILED
        if status not in {AgentStatus.COMPLETED, AgentStatus.FAILED, AgentStatus.BLOCKED}:
            status = AgentStatus.FAILED
        return AgentResult(
            task_id=task.task_id, status=status, output=str(getattr(raw, "output", "")),
            evidence=tuple(getattr(raw, "evidence", ()) or ()), artifacts=tuple(getattr(raw, "artifacts", ()) or ()),
            tests=tuple(getattr(raw, "tests", ()) or ()), risks=tuple(getattr(raw, "risks", ()) or ()),
            errors=tuple(getattr(raw, "errors", ()) or ()), cost=float(getattr(raw, "cost", 0.0) or 0.0),
            duration_ms=int(getattr(raw, "duration_ms", 0) or 0), verdict=getattr(raw, "verdict", None),
        )


class OpenHandsRuntimeAdapter:
    """Expose the existing OHOrchestrator as an AgentHandler-compatible callable."""
    def __init__(self, orchestrator: Any, *, title: str | None = None, description: str | None = None) -> None:
        self.orchestrator = orchestrator
        self.title = title
        self.description = description

    def __call__(self, task: AgentTask) -> AgentResult:
        try:
            result = self.orchestrator.run(task_id=task.task_id, title=self.title or task.goal[:120], description=self.description or task.goal)
        except Exception as exc:
            return AgentResult(task_id=task.task_id, status=AgentStatus.FAILED, errors=(f"{type(exc).__name__}: {exc}",))
        status_map = {"completed": AgentStatus.COMPLETED, "failed": AgentStatus.FAILED, "cancelled": AgentStatus.BLOCKED}
        status = status_map.get(str(result.status).lower(), AgentStatus.FAILED)
        report = result.report
        errors = tuple(x for x in (result.error, report.last_error if report else None) if x)
        return AgentResult(
            task_id=task.task_id, status=status, output=report.reason if report else str(result.status),
            artifacts=tuple(result.extras.artifacts), errors=errors,
            verdict="APPROVED" if status is AgentStatus.COMPLETED else "CHANGES_REQUESTED",
        )
