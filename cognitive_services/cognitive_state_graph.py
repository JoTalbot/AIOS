"""AIOS v23.2 Cognitive State Graph foundation."""


class CognitiveStateGraph:
    """Graph-based representation of agent cognitive state."""

    def __init__(self):
        self.nodes = {}
        self.edges = []

    def add_state(self, name, data=None):
        self.nodes[name] = data or {}

    def connect(self, source, target, relation="related"):
        self.edges.append({"source": source, "target": target, "relation": relation})

    def snapshot(self):
        return {"nodes": self.nodes, "edges": self.edges}
