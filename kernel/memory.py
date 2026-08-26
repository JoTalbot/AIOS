from collections import deque


class MemoryOS:
    """AIOS memory layer: short term and long term storage interface."""

    def __init__(self, max_short=100):
        self.short_memory = deque(maxlen=max_short)
        self.long_memory = []

    def remember(self, item, permanent=False):
        self.short_memory.append(item)
        if permanent:
            self.long_memory.append(item)

    def recall(self, query=None):
        if query is None:
            return list(self.short_memory)

        return [
            item for item in self.long_memory
            if query.lower() in str(item).lower()
        ]
