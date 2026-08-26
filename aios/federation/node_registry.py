"""AIOS Federation node registry."""

from dataclasses import dataclass, field
from typing import Dict


@dataclass
class FederationNode:
    node_id: str
    metadata: Dict[str, str] = field(default_factory=dict)


class NodeRegistry:
    def __init__(self):
        self.nodes: Dict[str, FederationNode] = {}

    def register(self, node: FederationNode) -> None:
        self.nodes[node.node_id] = node

    def get(self, node_id: str):
        return self.nodes.get(node_id)
