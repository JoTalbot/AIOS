class LongTermMemory:
    """AIOS long term memory foundation."""

    def __init__(self):
        self.storage = []

    def save(self, knowledge):
        self.storage.append(knowledge)

    def search(self):
        return self.storage
