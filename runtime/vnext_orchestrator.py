"""AIOS vNext end-to-end orchestration boundary."""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class OrchestrationResult:
    goal: str
    task_id: str
    status: str
    result: Any = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class VNextOrchestrator:
    """Coordinates planning, scheduling, execution and bounded reflection."""

    def __init__(self, planner, scheduler, agent, reflection=None, execution=None):
        self.planner = planner
        self.scheduler = scheduler
        self.agent = agent
        self.reflection = reflection
        self.execution = execution
        if execution is not None:
            self.scheduler.executor = execution.execute

    async def run(self, goal: str, task_id: str, metadata: Optional[Dict[str, Any]] = None):
        context = dict(metadata or {})
        plan = await self.planner.create_plan(goal)
        context["plan"] = plan
        task = self._build_task(task_id, goal, plan, context)
        await self.scheduler.submit(task)
        await self.scheduler.run_until_idle()
        if task.state.value == "failed":
            return OrchestrationResult(goal, task_id, "failed", metadata=context)
        result = task.payload.get("result")
        if self.reflection:
            context["reflection"] = await self.reflection.evaluate([result])
        return OrchestrationResult(goal, task_id, "completed", result, context)

    def _build_task(self, task_id, goal, plan, context):
        from kernel.scheduler import AgentTask
        return AgentTask(
            id=task_id,
            agent=str(self.agent),
            payload={
                "task_id": task_id,
                "goal": goal,
                "plan": plan,
                "context": context,
                "agent": self.agent,
            },
        )
