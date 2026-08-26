"""Execution coordinator for AIOS vNext.

Coordinates agent, tool, memory and event layers through explicit dependencies.
"""


class ExecutionCoordinator:
    def __init__(self, agent_runner=None, tool_manager=None, memory=None, events=None, supervisor=None):
        self.agent_runner = agent_runner
        self.tool_manager = tool_manager
        self.memory = memory
        self.events = events
        self.supervisor = supervisor

    async def execute(self, request):
        if self.supervisor:
            self.supervisor.on_start(request)
        try:
            self._publish("execution.started", request)
            context = request.get("context", {})
            goal = request.get("goal")
            plan = request.get("plan", [])
            self._remember({"type": "execution_started", "task_id": request.get("task_id"), "goal": goal})

            result = await self._run_agent(goal, plan, context)
            result = await self._run_tools(result, context)

            completed = {"request": request, "result": result, "status": "completed"}
            self._remember({"type": "execution_completed", "task_id": request.get("task_id"), "result": result}, permanent=True)
            self._publish("execution.completed", completed)
            if self.supervisor:
                self.supervisor.on_success(completed)
            return completed
        except Exception as error:
            recovery = self.supervisor.on_failure(error) if self.supervisor else None
            self._publish("execution.recovery_requested", {"error": str(error), "recovery": recovery})
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
