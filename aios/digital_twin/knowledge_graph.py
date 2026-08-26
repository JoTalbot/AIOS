"""Small dependency-free graph for Digital Twin entities and relations."""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple


@dataclass
class KnowledgeGraph:
    nodes: Dict[str, Dict] = field(default_factory=dict)
    edges: List[Tuple[str, str, str]] = field(default_factory=list)

    def add_node(self, node_id: str, metadata: Dict | None = None) -> None:
        self.nodes[node_id] = metadata or {}

    def add_edge(self, source: str, relation: str, target: str) -> None:
        if source in self.nodes and target in self.nodes:
            self.edges.append((source, relation, target))
