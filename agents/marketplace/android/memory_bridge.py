class MemoryBridge:
    """Bridge OLX agent data with AIOS memory layer."""

    def __init__(self, memory=None):
        self.memory = memory

    def remember_listing(self, listing):
        if self.memory:
            return self.memory.remember(listing)
        return listing

    def recall_context(self, query):
        if self.memory:
            return self.memory.recall(query)
        return []
