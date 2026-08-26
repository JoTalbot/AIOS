"""AIOS v21 world model foundation."""

from dataclasses import dataclass, field


@dataclass
class WorldState:
    facts: dict = field(default_factory=dict)


class WorldModel:
    def __init__(self):
        self.state = WorldState()

    def update(self, key: str, value):
        self.state.facts[key] = value

    def query(self, key: str):
        return self.state.facts.get(key)
