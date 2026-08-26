"""Execution coordinator for AIOS vNext."""

from execution.event_sink import ExecutionEventSink
from execution.events import EXECUTION_COMPLETED, EXECUTION_FAILED, EXECUTION_RECOVERY, EXECUTION_STARTED, build_event
from execution.memory_adapter import ExecutionMemoryAdapter
from execution.persistence import ExecutionStore
from execution.result import ExecutionResult
from execution.tool_adapter import ExecutionToolAdapter


class ExecutionCoordinator:
    def __init__(self, agent_runner=None, tool_manager=None, memory=None, events=None, supervisor=None, event_sink=None, persistence=None):
        self.agent_runner = agent_runner
        self.tool_manager = tool_manager
        self.memory = ExecutionMemoryAdapter(memory)
        self.events = events
        self.supervisor = supervisor
        self.event_sink = event_sink or ExecutionEventSink()
        self.persistence = persistence or ExecutionStore()

    async def execute(self, request):
        task_id = request.get("task_id", "unknown")
        persisted = self.persistence.load_result(task_id)
        if persisted is not None:
            return persisted
        try:
            self._emit(EXECUTION_STARTED, task_id)
            self._publish("execution.started", request)
            remembered = self.memory.recall(request.get("memory_query", request.get("goal")))
            context = dict(request.get("context") or {})
            context["task_id"] = task_id
            if remembered:
                context["memory"] = remembered
            self._remember({"type": "execution_started", "task_id": task_id, "goal": request.get("goal")})
            value = await self._run_agent(request.get("goal"), request.get("plan", []), context)
            value = await self._run_tools(value, context, request)
            result = value if isinstance(value, ExecutionResult) else ExecutionResult.success(task_id, value=value)
            result_dict = result.to_dict()
            self.persistence.save_result(task_id, result_dict)
            self._remember({"type": "execution_completed", "task_id": task_id, "result": result_dict}, permanent=True)
            self._observe("execution", "success", result)
            self._emit(EXECUTION_COMPLETED, task_id, **result.to_event_payload())
            self._publish("execution.completed", result.to_event_payload())
            return result_dict
        except Exception as error:
            result = ExecutionResult.failure(task_id, error)
            self._remember({"type": "execution_failed", "task_id": task_id, "error": result.error}, permanent=True)
            recovery = self._observe("execution", "failure", error)
            self._emit(EXECUTION_RECOVERY, task_id, error=result.error, recovery=recovery)
            self._emit(EXECUTION_FAILED, task_id, **result.to_event_payload())
            self._publish("execution.recovery_requested", {"result": result.to_event_payload(), "recovery": recovery})
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

    async def _run_tools(self, result, context, request):
        if not self.tool_manager:
            return result
        if isinstance(self.tool_manager, ExecutionToolAdapter):
            tool_name = request.get("tool") or request.get("tool_name")
            if not tool_name:
                return result
            return await self.tool_manager.execute(tool_name, request.get("arguments"), context=context)
        if hasattr(self.tool_manager, "execute"):
            value = self.tool_manager.execute(result, context=context)
            return await value if hasattr(value, "__await__") else value
        return result

    def _remember(self, item, permanent=False):
        self.memory.remember(item, permanent=permanent)

    def _publish(self, event, payload):
        if self.events and hasattr(self.events, "publish"):
            self.events.publish(event, payload=payload, source="execution-coordinator")

    def _observe(self, component, event, payload=None):
        if self.supervisor and hasattr(self.supervisor, "observe"):
            return self.supervisor.observe(component, event, payload)
        return None
