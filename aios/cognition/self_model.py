"""Self model for AIOS cognitive layer."""

from dataclasses import dataclass, field


@dataclass
class SelfModel:
    identity: str
    capabilities: list[str] = field(default_factory=list)
    state: dict = field(default_factory=dict)

    def update_state(self, key: str, value):
        self.state[key] = value
