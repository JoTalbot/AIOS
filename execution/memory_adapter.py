"""Adapter that keeps execution memory behind a small stable contract."""


class ExecutionMemoryAdapter:
    def __init__(self, memory=None):
        self.memory = memory

    def remember(self, item, permanent=False):
        if self.memory is None or not hasattr(self.memory, "remember"):
            return None
        return self.memory.remember(item, permanent=permanent)

    def recall(self, query=None):
        if self.memory is None or not hasattr(self.memory, "recall"):
            return []
        return self.memory.recall(query)
