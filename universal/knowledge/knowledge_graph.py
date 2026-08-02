class KnowledgeGraph:
    """Universal knowledge graph foundation."""

    def __init__(self):
        self.nodes = {}

    def add(self, key, value):
        self.nodes[key] = value

    def query(self, key):
        return self.nodes.get(key)
