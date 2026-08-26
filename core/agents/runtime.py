"""Agent runtime controller for lifecycle-aware execution."""

from enum import Enum


class AgentRuntimeState(str, Enum):
    CREATED = "created"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
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

    def transition(self, state):
        self.state = state
        self._emit(
            "agent.state_changed",
            {"agent": self.agent.name, "state": state.value},
        )
        return self.state

    def prepare(self):
        return self.transition(AgentRuntimeState.READY)

    def start(self):
        return self.transition(AgentRuntimeState.RUNNING)

    def pause(self):
        return self.transition(AgentRuntimeState.PAUSED)

    def stop(self):
        return self.transition(AgentRuntimeState.STOPPED)

    def fail(self, error=None):
        self.error = error
        self.transition(AgentRuntimeState.FAILED)
        self._emit("agent.failed", {"agent": self.agent.name, "error": error})
        return self.state

    def execute(self, request):
        if self.state not in (
            AgentRuntimeState.RUNNING,
            AgentRuntimeState.READY,
        ):
            self.start()
        try:
            result = self.agent.execute(request)
            self._emit("agent.execution.completed", {"agent": self.agent.name})
            return result
        except Exception as error:
            self.fail(error)
            raise
