"""AIOS v23.4 Agent Communication Protocol.

Defines a minimal communication boundary for multi-agent coordination.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass
class AgentMessage:
    sender: str
    receiver: str
    payload: Any
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


class AgentCommunicationProtocol:
    def send(self, message: AgentMessage) -> dict:
        return {
            "status": "delivered",
            "sender": message.sender,
            "receiver": message.receiver,
        }

    def broadcast(self, sender: str, payload: Any, agents: list[str]) -> list[dict]:
        return [
            self.send(AgentMessage(sender=sender, receiver=agent, payload=payload))
            for agent in agents
        ]
