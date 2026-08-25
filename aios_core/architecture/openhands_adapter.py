"""Govern OpenHands contour execution as an ArchitectureRuntime capability."""

from __future__ import annotations

from typing import Any, Protocol

from aios_core.execution import Action, ExecutionContext, Observation

from .runtime import ArchitectureRuntime

OPENHANDS_RUN_CAPABILITY = "openhands_cloud_run"


class ContourProtocol(Protocol):
    def run_task(self, task_id: str) -> Any: ...


class OpenHandsCapabilityAdapter:
    """CapabilityEngine-compatible adapter around ContourService.run_task."""

    def __init__(self, contour: ContourProtocol) -> None:
        self.contour = contour
        self.calls = 0

    def execute(
        self,
        *,
        capability_name: str,
        input_data: dict[str, Any],
        agent_id: str,
        authority: str,
    ) -> dict[str, Any]:
        if capability_name != OPENHANDS_RUN_CAPABILITY:
            return {"success": False, "error": "unsupported_openhands_capability", "result": None}
        task_id = str(input_data.get("task_id") or "")
        if not task_id:
            return {"success": False, "error": "openhands_task_id_required", "result": None}
        self.calls += 1
        result = self.contour.run_task(task_id)
        status = str(getattr(result, "status", ""))
        success = status == "completed"
        return {
            "success": success,
            "result": result,
            "error": None if success else (getattr(result, "error", None) or f"openhands_status:{status}"),
        }


class GovernedOpenHandsRunner:
    """Public run boundary; never calls ContourService directly."""

    def __init__(self, runtime: ArchitectureRuntime) -> None:
        self.runtime = runtime

    def run(
        self,
        task_id: str,
        *,
        agent_id: str,
        authority: str = "operator",
        action_id: str | None = None,
    ) -> Observation:
        return self.runtime.execute(
            Action(OPENHANDS_RUN_CAPABILITY, {"task_id": task_id}, id=action_id or f"openhands-{task_id}"),
            ExecutionContext(task_id=task_id, agent_id=agent_id, authority=authority),
        )
