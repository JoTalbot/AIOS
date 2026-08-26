"""Agent runtime controller for lifecycle-aware execution."""

from enum import Enum


class AgentRuntimeState(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    STOPPED = "stopped"
    FAILED = "failed"


class AgentRuntime:
    """Controls agent lifecycle and execution state."""

    def __init__(self, agent):
        self.agent = agent
        self.state = AgentRuntimeState.CREATED

    def start(self):
        self.state = AgentRuntimeState.RUNNING
        return self.state

    def stop(self):
        self.state = AgentRuntimeState.STOPPED
        return self.state

    def fail(self, error=None):
        self.error = error
        self.state = AgentRuntimeState.FAILED
        return self.state

    def execute(self, request):
        if self.state != AgentRuntimeState.RUNNING:
            self.start()
        return self.agent.execute(request)
