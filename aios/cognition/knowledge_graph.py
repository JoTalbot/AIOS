"""Knowledge graph foundation for AIOS Cognitive Layer v21."""

from dataclasses import dataclass, field


@dataclass
class KnowledgeGraph:
    nodes: dict[str, dict] = field(default_factory=dict)
    edges: list[tuple[str, str]] = field(default_factory=list)

    def add_node(self, name: str, data: dict | None = None):
        self.nodes[name] = data or {}

    def connect(self, source: str, target: str):
        self.edges.append((source, target))

    def related(self, node: str):
        return [b for a, b in self.edges if a == node]
