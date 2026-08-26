"""Federated intelligence primitives for Digital Twin state exchange."""

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class TwinStateExchange:
    states: Dict[str, Dict] = field(default_factory=dict)

    def publish(self, node_id: str, state: Dict) -> None:
        self.states[node_id] = dict(state)

    def snapshot(self) -> Dict[str, Dict]:
        return {node: dict(state) for node, state in self.states.items()}

    def active_nodes(self) -> List[str]:
        return sorted(self.states)
