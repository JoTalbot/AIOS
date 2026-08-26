from dataclasses import dataclass
from datetime import datetime


@dataclass
class Capability:
    name: str
    scope: list[str]
    risk: str = "medium"
    expires: datetime | None = None

    def valid(self) -> bool:
        if self.expires is None:
            return True
        return datetime.utcnow() < self.expires


class CapabilityEngine:
    def __init__(self):
        self.capabilities = {}

    def register(self, agent_id: str, capability: Capability):
        self.capabilities.setdefault(agent_id, []).append(capability)

    def check(self, agent_id: str, capability_name: str) -> bool:
        return any(
            c.name == capability_name and c.valid()
            for c in self.capabilities.get(agent_id, [])
        )
