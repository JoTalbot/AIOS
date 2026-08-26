"""Bounded autonomous execution loop with restart-safe persistence."""

from dataclasses import dataclass
from typing import Any, Optional

from .execution_context import ExecutionContext
from .execution_store import ExecutionState, ExecutionStore
from .event_types import REPLAN_COMPLETED, REPLAN_REQUESTED
from .execution_events import ExecutionEvent
from .replanning import ReplanningPolicy


@dataclass(frozen=True)
class LoopResult:
    status: str
    result: Any = None
    attempts: int = 0


class AutonomousExecutionLoop:
    """Execute plans, persist checkpoints, and recover running executions."""

    def __init__(self, executor, planner, policy: Optional[ReplanningPolicy] = None, event_bus=None, store: Optional[ExecutionStore] = None):
        self.executor = executor
        self.planner = planner
        self.policy = policy or ReplanningPolicy()
        self.event_bus = event_bus
        self.store = store

    async def run(self, goal: str, agent: Any, context: Optional[dict] = None, execution_context: Optional[ExecutionContext] = None):
        context = dict(context or {})
        execution = execution_context or ExecutionContext(agent_id=str(getattr(agent, "id", None) or agent), goal=goal, metadata=context)
        plan = await self.planner.create_plan(goal)
        return await self._run_from_state(goal, agent, context, execution, plan, 0)

    async def resume(self, execution_id: str, agent: Any, context: Optional[dict] = None):
        if not self.store:
            raise RuntimeError("execution store is required for resume")
        state = self.store.get(execution_id)
        if not state or state.status != "running":
            raise ValueError(f"execution '{execution_id}' is not resumable")
        execution = ExecutionContext(execution_id=state.execution_id, agent_id=str(getattr(agent, "id", None) or agent), goal=state.goal, metadata=dict(context or {}))
        return await self._run_from_state(state.goal, agent, dict(context or {}), execution, state.plan, state.attempt)

    async def _run_from_state(self, goal, agent, context, execution, plan, start_attempt):
        for attempt in range(start_attempt, self.policy.max_attempts):
            self._save(execution, "running", goal, attempt, plan)
            results = await self.executor.execute(agent, plan, context, execution)
            failed = next((r for r in results if hasattr(r, "ok") and not r.ok), None)
            if failed is None:
                self._save(execution, "completed", goal, attempt + 1, plan, results)
                return LoopResult("completed", results, attempt + 1)
            decision = self.policy.decide(attempt, RuntimeError(failed.error or "tool execution failed"))
            await self._publish(REPLAN_REQUESTED, execution, {"attempt": attempt, "error": failed.error})
            if not decision.retry:
                self._save(execution, "failed", goal, attempt + 1, plan, results, failed.error)
                return LoopResult("failed", results, attempt + 1)
            plan = await self.planner.create_plan(f"{goal} [replan attempt {attempt + 1}]")
            self._save(execution, "running", goal, attempt + 1, plan)
            await self._publish(REPLAN_COMPLETED, execution, {"attempt": attempt + 1, "plan": plan})
        self._save(execution, "failed", goal, self.policy.max_attempts, plan)
        return LoopResult("failed", attempts=self.policy.max_attempts)

    def _save(self, execution, status, goal, attempt, plan, result=None, error=None):
        if self.store:
            self.store.save(ExecutionState(execution.execution_id, status=status, goal=goal, attempt=attempt, plan=plan, result=result, error=error))

    async def _publish(self, event_type, context, data):
        if self.event_bus:
            await self.event_bus.publish(event_type, ExecutionEvent(event_type, context, data))
