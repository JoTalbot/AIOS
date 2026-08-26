"""AIOS v24.2 Collective Memory Optimization Layer.

Provides a lightweight foundation for consolidating shared swarm knowledge.
"""


class CollectiveMemoryOptimizer:
    def __init__(self):
        self.knowledge = []

    def add_memory(self, item):
        self.knowledge.append(item)

    def consolidate(self):
        return list(dict.fromkeys(self.knowledge))

    def recall(self):
        return self.consolidate()
