class MemoryReasoner:
    """Bridge between memory systems and cognitive reasoning."""

    def __init__(self, memory=None):
        self.memory = memory

    def query_context(self, query):
        if self.memory and hasattr(self.memory, "recall"):
            return self.memory.recall(query)
        return []
