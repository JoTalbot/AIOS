from dataclasses import dataclass, field
from typing import Dict, Any


@dataclass
class AgentMessage:
    sender: str
    receiver: str
    message_type: str
    payload: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0
