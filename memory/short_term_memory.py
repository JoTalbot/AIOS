class ShortTermMemory:
    """AIOS short term memory foundation."""

    def __init__(self):
        self.items = []

    def store(self, item):
        self.items.append(item)

    def recall(self):
        return self.items
