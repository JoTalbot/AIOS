class SemanticMemory:
    """Knowledge memory foundation."""

    def __init__(self):
        self.knowledge = {}

    def add(self, key, value):
        self.knowledge[key] = value

    def get(self, key):
        return self.knowledge.get(key)
