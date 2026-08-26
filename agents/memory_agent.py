class MemoryAgent:
    def __init__(self, memory_store=None):
        self.memory_store = memory_store

    def remember(self, item):
        if self.memory_store:
            return self.memory_store.store(item)
        return item

    def recall(self, query=None):
        if self.memory_store:
            return self.memory_store.search(query)
        return []
