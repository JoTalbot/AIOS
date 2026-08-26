from dataclasses import dataclass
from datetime import datetime


@dataclass
class AgentPacket:
    sender: str
    receiver: str
    action: str
    payload: dict
    created_at: datetime
