"""Orchestrator integration helpers for the execution kernel.

This module provides the narrow adapter used by the orchestrator integration
without changing the existing step-handler registry in place.  It converts a
tool step into an immutable Action and returns the kernel Observation.
"""

from __future__ import annotations

from typing import Any

from .kernel import ExecutionContext, ExecutionKernel
from .models import Action, Observation


def execute_tool_step(
    kernel: ExecutionKernel,
    *,
    task_id: str,
    agent_id: str,
    authority: str,
    params: dict[str, Any],
) -> Observation:
    """Execute a tool step through the canonical execution boundary.

    ``params`` uses the stable public shape ``capability`` + ``arguments``.
    The adapter deliberately does not mutate the supplied mapping.
    """
    capability = params.get("capability")
    if not capability:
        raise ValueError("Tool step requires a 'capability' parameter")

    arguments = params.get("arguments", {})
    if not isinstance(arguments, dict):
        raise TypeError("Tool step 'arguments' must be a dict")

    action = Action(capability=capability, arguments=dict(arguments))
    context = ExecutionContext(
        task_id=task_id,
        agent_id=agent_id,
        authority=authority,
    )
    return kernel.execute(action, context)
