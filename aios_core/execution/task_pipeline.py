"""AIOS unified task execution pipeline."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict


@dataclass
class PipelineResult:
    task_id: str
    status: str
    output: Any = None
    error: str | None = None
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class TaskPipeline:
    """Coordinates task execution stages."""

    def __init__(self, router=None, executor=None, memory=None):
        self.router = router
        self.executor = executor
        self.memory = memory

    async def run(self, task: Dict[str, Any]) -> PipelineResult:
        task_id = task.get("id", "unknown")
        try:
            routed = task
            if self.router:
                routed = await self.router.route(task)

            result = routed
            if self.executor:
                result = await self.executor.execute(routed)

            if self.memory:
                await self.memory.store(task_id, result)

            return PipelineResult(task_id=task_id, status="completed", output=result)
        except Exception as exc:
            return PipelineResult(task_id=task_id, status="failed", error=str(exc))
