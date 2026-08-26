"""Bounded autonomous execution loop for AIOS vNext."""

from dataclasses import dataclass
from typing import Any, Optional

from .execution_context import ExecutionContext
from .event_types import REPLAN_COMPLETED, REPLAN_REQUESTED
from .execution_events import ExecutionEvent
from .replanning import ReplanningPolicy


@dataclass(frozen=True)
class LoopResult:
    status: str
    result: Any = None
    attempts: int = 0


class AutonomousExecutionLoop:
    """Execute plans and automatically replan after failed tool results."""

    def __init__(self, executor, planner, policy: Optional[ReplanningPolicy] = None, event_bus=None):
        self.executor = executor
        self.planner = planner
        self.policy = policy or ReplanningPolicy()
        self.event_bus = event_bus

    async def run(self, goal: str, agent: Any, context: Optional[dict] = None, execution_context: Optional[ExecutionContext] = None):
        context = dict(context or {})
        execution = execution_context or ExecutionContext(agent_id=str(getattr(agent, "id", None) or agent), goal=goal, metadata=context)
        plan = await self.planner.create_plan(goal)
        for attempt in range(self.policy.max_attempts):
            results = await self.executor.execute(agent, plan, context, execution)
            failed = next((r for r in results if hasattr(r, "ok") and not r.ok), None)
            if failed is None:
                return LoopResult("completed", results, attempt + 1)
            decision = self.policy.decide(attempt, RuntimeError(failed.error or "tool execution failed"))
            await self._publish(REPLAN_REQUESTED, execution, {"attempt": attempt, "error": failed.error})
            if not decision.retry:
                return LoopResult("failed", results, attempt + 1)
            plan = await self.planner.create_plan(f"{goal} [replan attempt {attempt + 1}]")
            await self._publish(REPLAN_COMPLETED, execution, {"attempt": attempt + 1, "plan": plan})
        return LoopResult("failed", attempts=self.policy.max_attempts)

    async def _publish(self, event_type, context, data):
        if self.event_bus:
            await self.event_bus.publish(event_type, ExecutionEvent(event_type, context, data))
