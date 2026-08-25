"""Adapter that exposes OpenHands through the common AIOS runtime contract."""

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
            return AgentResult(
                task_id=task.task_id,
                status=AgentStatus.FAILED,
                errors=(f"{type(exc).__name__}: {exc}",),
            )

        status = getattr(raw, "status", AgentStatus.COMPLETED)
        if isinstance(status, str):
            try:
                status = AgentStatus(status.lower())
            except ValueError:
                status = AgentStatus.FAILED
        if status not in {AgentStatus.COMPLETED, AgentStatus.FAILED, AgentStatus.BLOCKED}:
            status = AgentStatus.FAILED

        return AgentResult(
            task_id=task.task_id,
            status=status,
            output=str(getattr(raw, "output", "")),
            evidence=tuple(getattr(raw, "evidence", ()) or ()),
            artifacts=tuple(getattr(raw, "artifacts", ()) or ()),
            tests=tuple(getattr(raw, "tests", ()) or ()),
            risks=tuple(getattr(raw, "risks", ()) or ()),
            errors=tuple(getattr(raw, "errors", ()) or ()),
            cost=float(getattr(raw, "cost", 0.0) or 0.0),
            duration_ms=int(getattr(raw, "duration_ms", 0) or 0),
            verdict=getattr(raw, "verdict", None),
        )
