"""AIOS Knowledge Graph Layer v2.1.1

Stores relations between rules, knowledge and system experience.
"""


class KnowledgeGraph:
    """Manages knowledge graph of rules and relationships."""

    def __init__(self):
        self.nodes = []
        self.edges = []

    def add_node(self, node: dict):
        """Add a node to the knowledge graph."""
        node["id"] = len(self.nodes)
        self.nodes.append(node)
        return node

    def add_relation(self, source: str, target: str, relation: str):
        """Add a relationship between nodes."""
        edge = {
            "source": source,
            "target": target,
            "relation": relation,
            "id": len(self.edges)
        }
        self.edges.append(edge)
        return edge

    def related(self, node_id: str) -> list:
        """Find all related nodes."""
        return [
            e for e in self.edges 
            if e["source"] == node_id or e["target"] == node_id
        ]
