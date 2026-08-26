"""Execution kernel boundary.

Provides a stable contract between orchestration and runtime execution layers.
"""

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass
class ExecutionResult:
    """Normalized result returned by execution."""

    success: bool
    value: Any = None
    error: Exception | None = None


class ExecutionRuntime(Protocol):
    async def execute(self, context: Any) -> Any:
        ...


class ExecutionBoundary:
    """Single entry point for task execution."""

    def __init__(self, runtime: ExecutionRuntime):
        self.runtime = runtime

    async def execute(self, context: Any) -> ExecutionResult:
        try:
            value = await self.runtime.execute(context)
            return ExecutionResult(success=True, value=value)
        except Exception as exc:
            return ExecutionResult(success=False, error=exc)
