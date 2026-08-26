"""AIOS v22.7 Persistent Agent Memory Layer.

Provides a minimal abstraction for storing and recalling agent experiences.
"""


class PersistentMemory:
    def __init__(self):
        self._records = []

    def store(self, record):
        self._records.append(record)
        return record

    def recall(self):
        return list(self._records)

    def clear(self):
        self._records = []
