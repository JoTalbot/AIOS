"""Execution coordinator for AIOS.

Coordinates agent, tool, memory and event layers.
"""


class ExecutionCoordinator:
    def __init__(self, agent_runner=None, tool_manager=None, memory=None, events=None, supervisor=None):
        self.agent_runner = agent_runner
        self.tool_manager = tool_manager
        self.memory = memory
        self.events = events
        self.supervisor = supervisor

    def execute(self, request):
        if self.supervisor:
            self.supervisor.on_start(request)

        try:
            if self.events:
                self.events.publish("execution.started", request)

            result = {"request": request, "status": "completed"}

            if self.events:
                self.events.publish("execution.completed", result)

            if self.supervisor:
                self.supervisor.on_success(result)

            return result
        except Exception as error:
            recovery = None
            if self.supervisor:
                recovery = self.supervisor.on_failure(error)

            if self.events:
                self.events.publish(
                    "execution.recovery_requested",
                    {"error": str(error), "recovery": recovery},
                )

            raise
