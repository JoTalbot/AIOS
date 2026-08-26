"""Execution coordinator for AIOS vNext."""

from execution.event_sink import ExecutionEventSink
from execution.events import EXECUTION_COMPLETED, EXECUTION_FAILED, EXECUTION_RECOVERY, EXECUTION_STARTED, build_event
from execution.result import ExecutionResult


class ExecutionCoordinator:
    def __init__(self, agent_runner=None, tool_manager=None, memory=None, events=None, supervisor=None, event_sink=None):
        self.agent_runner = agent_runner
        self.tool_manager = tool_manager
        self.memory = memory
        self.events = events
        self.supervisor = supervisor
        self.event_sink = event_sink or ExecutionEventSink()

    async def execute(self, request):
        task_id = request.get("task_id", "unknown")
        try:
            self._emit(EXECUTION_STARTED, task_id)
            self._publish("execution.started", request)
            self._remember({"type": "execution_started", "task_id": task_id, "goal": request.get("goal")})
            value = await self._run_agent(request.get("goal"), request.get("plan", []), request.get("context", {}))
            value = await self._run_tools(value, request.get("context", {}))
            result = ExecutionResult.success(task_id, value=value)
            self._remember({"type": "execution_completed", "task_id": task_id, "result": value}, permanent=True)
            self._observe("execution", "success", result)
            self._emit(EXECUTION_COMPLETED, task_id, status=result.status)
            self._publish("execution.completed", result.__dict__)
            return result.__dict__
        except Exception as error:
            result = ExecutionResult.failure(task_id, error)
            self._remember({"type": "execution_failed", "task_id": task_id, "error": str(error)}, permanent=True)
            recovery = self._observe("execution", "failure", error)
            self._emit(EXECUTION_RECOVERY, task_id, error=str(error), recovery=recovery)
            self._emit(EXECUTION_FAILED, task_id, error=str(error), status=result.status)
            self._publish("execution.recovery_requested", {"result": result.__dict__, "recovery": recovery})
            raise

    def _emit(self, event_type, task_id, **data):
        return self.event_sink.emit(build_event(event_type, task_id, **data))

    async def _run_agent(self, goal, plan, context):
        runner = self.agent_runner
        if runner is None:
            return {"goal": goal, "plan": plan, "context": context}
        for name in ("run", "execute"):
            method = getattr(runner, name, None)
            if method:
                value = method(goal=goal, plan=plan, context=context)
                return await value if hasattr(value, "__await__") else value
        value = runner(goal, plan, context) if callable(runner) else None
        return await value if hasattr(value, "__await__") else value

    async def _run_tools(self, result, context):
        if not self.tool_manager or not hasattr(self.tool_manager, "execute"):
            return result
        value = self.tool_manager.execute(result, context=context)
        return await value if hasattr(value, "__await__") else value

    def _remember(self, item, permanent=False):
        if self.memory and hasattr(self.memory, "remember"):
            self.memory.remember(item, permanent=permanent)

    def _publish(self, event, payload):
        if self.events and hasattr(self.events, "publish"):
            self.events.publish(event, payload=payload, source="execution-coordinator")

    def _observe(self, component, event, payload=None):
        if self.supervisor and hasattr(self.supervisor, "observe"):
            return self.supervisor.observe(component, event, payload)
        return None
