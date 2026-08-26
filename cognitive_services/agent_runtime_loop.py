"""AIOS v22.6 Agent Runtime Loop foundation.

Coordinates execution state transitions between planning, execution,
and reflection layers.
"""


class AgentRuntimeLoop:
    def __init__(self, state_manager=None, executor=None, reflector=None):
        self.state_manager = state_manager
        self.executor = executor
        self.reflector = reflector
        self.status = "idle"

    def run(self, workflow):
        self.status = "running"
        result = None
        if self.executor:
            result = self.executor.execute(workflow)
        if self.reflector:
            self.reflector.observe(result)
        self.status = "completed"
        return result

    def health(self):
        return {"service": "agent_runtime_loop", "status": self.status}
