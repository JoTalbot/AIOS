class VectorStore:
    """Vector memory storage foundation."""

    def __init__(self):
        self.items = []

    def add(self, vector, metadata=None):
        self.items.append({"vector": vector, "metadata": metadata or {}})

    def all(self):
        return self.items
