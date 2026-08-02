class CollectiveMemory:
    """Shared memory layer foundation."""

    def __init__(self):
        self.memories = []

    def store(self, memory):
        self.memories.append(memory)

    def recall(self):
        return self.memories
