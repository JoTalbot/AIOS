"""Bridge between Orchestrator task steps and the execution kernel.

The bridge keeps orchestration concerns (task/agent identity and step
parameters) outside the kernel while providing a single callable boundary for
future direct integration in ``Orchestrator._execute_step``.
"""

from __future__ import annotations

from typing import Any

from .kernel import ExecutionKernel
from .models import Observation
from .orchestrator_adapter import execute_tool_step


class OrchestratorExecutionBridge:
    """Execute an orchestrator tool step through ``ExecutionKernel``."""

    def __init__(self, kernel: ExecutionKernel):
        self.kernel = kernel

    def execute(self, task: Any, step: Any) -> Observation:
        """Map an AIOS task/step pair onto the canonical execution boundary."""
        return execute_tool_step(
            self.kernel,
            task_id=task.id,
            agent_id=task.agent_id,
            authority=task.authority,
            params=step.params,
        )
