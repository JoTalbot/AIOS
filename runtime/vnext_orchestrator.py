"""AIOS vNext end-to-end orchestration boundary."""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .agent_executor import AgentExecutor


@dataclass
class OrchestrationResult:
    goal: str
    task_id: str
    status: str
    result: Any = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class VNextOrchestrator:
    """Coordinates Intent -> Planner -> Scheduler -> Agent -> Tools -> Memory -> Reflection."""

    def __init__(self, planner, scheduler, agent, reflection=None, executor: Optional[AgentExecutor] = None, memory=None):
        self.planner = planner
        self.scheduler = scheduler
        self.agent = agent
        self.reflection = reflection
        self.executor = executor
        self.memory = memory

    async def run(self, goal: str, task_id: str, metadata: Optional[Dict[str, Any]] = None):
        context = dict(metadata or {})
        plan = await self.planner.create_plan(goal)
        context["plan"] = plan
        if self.memory and hasattr(self.memory, "remember"):
            self.memory.remember({"event": "plan.created", "task_id": task_id, "goal": goal, "plan": plan})
        task = self._build_task(task_id, goal, plan, context)
        await self.scheduler.submit(task)
        await self.scheduler.run_until_idle()
        if getattr(task, "state", None).value == "failed":
            return OrchestrationResult(goal, task_id, "failed", metadata=context)
        result = getattr(task, "payload", {}).get("result")
        if self.reflection:
            context["reflection"] = await self.reflection.evaluate([result])
        if self.memory and hasattr(self.memory, "remember"):
            self.memory.remember({"event": "task.completed", "task_id": task_id, "result": result})
        return OrchestrationResult(goal, task_id, "completed", result, context)

    def _build_task(self, task_id, goal, plan, context):
        from kernel.scheduler import AgentTask
        payload = {"goal": goal, "plan": plan, "context": context, "agent": self.agent}
        if self.executor:
            payload["executor"] = self.executor
        return AgentTask(id=task_id, agent=str(self.agent), payload=payload)
