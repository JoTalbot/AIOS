"""Agent runtime controller for lifecycle-aware execution."""

from enum import Enum


class AgentRuntimeState(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    STOPPED = "stopped"
    FAILED = "failed"


class AgentRuntime:
    """Controls agent lifecycle and execution state."""

    def __init__(self, agent, event_bus=None):
        self.agent = agent
        self.event_bus = event_bus
        self.state = AgentRuntimeState.CREATED
        self.error = None

    def _emit(self, name, payload=None):
        if self.event_bus:
            self.event_bus.publish(name, payload or {}, source="agent_runtime")

    def start(self):
        self.state = AgentRuntimeState.RUNNING
        self._emit("agent.started", {"agent": self.agent.name})
        return self.state

    def stop(self):
        self.state = AgentRuntimeState.STOPPED
        self._emit("agent.stopped", {"agent": self.agent.name})
        return self.state

    def fail(self, error=None):
        self.error = error
        self.state = AgentRuntimeState.FAILED
        self._emit("agent.failed", {"agent": self.agent.name, "error": error})
        return self.state

    def execute(self, request):
        if self.state != AgentRuntimeState.RUNNING:
            self.start()
        try:
            return self.agent.execute(request)
        except Exception as error:
            self.fail(error)
            raise
