"""Explicit integration boundary between Orchestrator and ExecutionKernel.

The helper keeps the integration small and testable until the legacy
Orchestrator module can be changed through a patch-aware workflow.
"""

from __future__ import annotations

from typing import Any

from .kernel import ExecutionKernel
from .orchestrator_adapter import execute_tool_step


def execute_orchestrator_tool_step(
    kernel: ExecutionKernel,
    task: Any,
    step: Any,
):
    """Route an Orchestrator Task/TaskStep pair through the kernel."""
    return execute_tool_step(
        kernel,
        task_id=task.id,
        agent_id=task.agent_id,
        authority=task.authority,
        params=step.params,
    )
