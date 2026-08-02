class KnowledgeNetwork:
    """Collective knowledge network foundation."""

    def __init__(self):
        self.knowledge = []

    def add(self, item):
        self.knowledge.append(item)

    def query(self):
        return self.knowledge
