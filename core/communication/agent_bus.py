"""Agent communication bus for AIOS multi-agent coordination."""

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class AgentMessage:
    sender: str
    receiver: str
    message_type: str
    payload: Dict[str, Any] = field(default_factory=dict)


class AgentBus:
    """Lightweight message router between AIOS agents."""

    def __init__(self):
        self.queue: List[AgentMessage] = []

    def send(self, message: AgentMessage) -> None:
        self.queue.append(message)

    def receive(self, receiver: str) -> List[AgentMessage]:
        messages = [m for m in self.queue if m.receiver == receiver]
        self.queue = [m for m in self.queue if m.receiver != receiver]
        return messages
