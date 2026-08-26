"""AIOS v20 agent lifecycle manager."""

from enum import Enum


class AgentStatus(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"


class AgentLifecycle:
    def __init__(self):
        self.states: dict[str, AgentStatus] = {}

    def create(self, agent_id: str) -> AgentStatus:
        self.states[agent_id] = AgentStatus.CREATED
        return self.states[agent_id]

    def transition(self, agent_id: str, status: AgentStatus) -> AgentStatus:
        self.states[agent_id] = status
        return status
