"""AIOS v22.1 Memory Adapter.

Connects cognitive workflows with the memory layer abstraction.
"""


class MemoryAdapter:
    def __init__(self, memory):
        self.memory = memory

    def store(self, record):
        return self.memory.store(record)

    def recall(self, query=None):
        return self.memory.recall(query)
