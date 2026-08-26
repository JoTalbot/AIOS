"""AIOS v23.6 Distributed Cognitive State Sync foundation."""

from typing import Dict, Any


class DistributedCognitiveStateSync:
    def __init__(self):
        self.states: Dict[str, Dict[str, Any]] = {}

    def publish_state(self, agent_id: str, state: Dict[str, Any]):
        self.states[agent_id] = state

    def get_state(self, agent_id: str):
        return self.states.get(agent_id)

    def snapshot(self):
        return dict(self.states)
