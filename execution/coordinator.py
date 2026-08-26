"""Execution coordinator for AIOS vNext.

Coordinates agent, tool, memory, event and supervision layers through one
explicit asynchronous execution boundary.
"""

from execution.result import ExecutionResult


class ExecutionCoordinator:
    def __init__(self, agent_runner=None, tool_manager=None, memory=None, events=None, supervisor=None):
        self.agent_runner = agent_runner
        self.tool_manager = tool_manager
        self.memory = memory
        self.events = events
        self.supervisor = supervisor

    async def execute(self, request):
        task_id = request.get("task_id", "unknown")
        try:
            self._observe("runtime", "start", request)
            self._publish("execution.started", request)
            context = request.get("context", {})
            goal = request.get("goal")
            plan = request.get("plan", [])
            self._remember({"type": "execution_started", "task_id": task_id, "goal": goal})

            value = await self._run_agent(goal, plan, context)
            value = await self._run_tools(value, context)
            result = ExecutionResult.success(task_id, value=value)
            self._remember({"type": "execution_completed", "task_id": task_id, "result": value}, permanent=True)
            self._publish("execution.completed", result.__dict__)
            self._observe("execution", "success", result)
            return result.__dict__
        except Exception as error:
            result = ExecutionResult.failure(task_id, error)
            self._remember({"type": "execution_failed", "task_id": task_id, "error": str(error)}, permanent=True)
            recovery = self._observe("execution", "failure", error)
            self._publish("execution.recovery_requested", {"result": result.__dict__, "recovery": recovery})
            raise

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
        manager = self.tool_manager
        if manager is None:
            return result
        method = getattr(manager, "execute", None)
        if method is None:
            return result
        value = method(result, context=context)
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
