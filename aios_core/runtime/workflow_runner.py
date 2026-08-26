"""AIOS Workflow Runner.

Executes ordered task workflows with shared execution context.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, List


@dataclass
class WorkflowResult:
    status: str
    results: list = field(default_factory=list)
    error: str | None = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class WorkflowRunner:
    def __init__(self):
        self.workflows = {}

    def register(self, name: str, steps: List[Callable]):
        self.workflows[name] = steps

    async def run(self, name: str, context: dict[str, Any] | None = None):
        if name not in self.workflows:
            return WorkflowResult(status="failed", error="workflow_not_found")

        context = context or {}
        results = []

        try:
            for step in self.workflows[name]:
                result = step(context)
                if hasattr(result, "__await__"):
                    result = await result
                results.append(result)

            return WorkflowResult(status="completed", results=results)
        except Exception as exc:
            return WorkflowResult(status="failed", error=str(exc))
