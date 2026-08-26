from dataclasses import dataclass


@dataclass
class KnowledgeEdge:
    source: str
    target: str
    relation: str


class SharedKnowledgeGraph:
    def __init__(self):
        self.nodes = set()
        self.edges = []

    def add_node(self, node):
        self.nodes.add(node)

    def connect(self, source, target, relation):
        self.edges.append(KnowledgeEdge(source, target, relation))

    def query(self, node):
        return [edge for edge in self.edges if edge.source == node]
