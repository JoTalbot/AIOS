class KnowledgeStore:
    """AIOS knowledge storage foundation."""

    def __init__(self):
        self.data = {}

    def store(self, key, value):
        self.data[key] = value

    def get(self, key):
        return self.data.get(key)
