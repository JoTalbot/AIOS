class LongTermMemory:
    """Universal long term memory foundation."""

    def __init__(self):
        self.memory = []

    def store(self, item):
        self.memory.append(item)

    def retrieve(self):
        return self.memory
