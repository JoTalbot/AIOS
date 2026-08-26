from typing import Dict, List

from .message import AgentMessage


class AgentBus:
    """Simple communication layer between AIOS agents."""

    def __init__(self):
        self.agents: Dict[str, List[AgentMessage]] = {}

    def register(self, agent_id: str):
        self.agents.setdefault(agent_id, [])

    def send(self, message: AgentMessage):
        self.agents.setdefault(message.receiver, []).append(message)

    def receive(self, agent_id: str) -> List[AgentMessage]:
        return self.agents.pop(agent_id, [])
