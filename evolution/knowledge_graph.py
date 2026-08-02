class KnowledgeGraph:
    """AIOS knowledge graph evolution foundation."""

    def __init__(self):
        self.nodes = {}

    def add(self, key, value):
        self.nodes[key] = value

    def get(self, key):
        return self.nodes.get(key)
