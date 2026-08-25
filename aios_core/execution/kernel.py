"""Thin execution boundary over the existing AIOS capability engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .models import Action, Observation


@dataclass(frozen=True)
class ExecutionContext:
    """Context supplied to a capability execution."""

    task_id: str
    agent_id: str
    authority: str = "system"


class ExecutionKernel:
    """Canonical entry point for external capability side effects.

    Policy remains responsible for the task-level constitutional decision while
    CapabilityEngine remains responsible for capability lifecycle, authority,
    handler resolution, and invocation. The kernel deliberately does not
    duplicate those responsibilities in v1.
    """

    def __init__(self, capabilities: Any):
        self.capabilities = capabilities

    def execute(self, action: Action, context: ExecutionContext) -> Observation:
        """Execute one action through the existing CapabilityEngine."""
        try:
            result = self.capabilities.execute(
                capability_name=action.capability,
                input_data=action.arguments,
                agent_id=context.agent_id,
                authority=context.authority,
            )

            # CapabilityEngine returns a structured execution envelope. Preserve
            # its success/error semantics instead of treating every returned
            # envelope as a successful observation.
            if isinstance(result, dict) and result.get("success") is False:
                return Observation(
                    action_id=action.id,
                    success=False,
                    result=result.get("result"),
                    error=result.get("error"),
                )

            return Observation.from_result(action, result)
        except Exception as exc:
            return Observation.failed(action, str(exc))
