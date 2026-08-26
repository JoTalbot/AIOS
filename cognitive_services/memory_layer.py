"""Memory abstraction for AIOS cognitive services."""


class CognitiveMemory:
    def __init__(self):
        self._entries = []

    def store(self, item):
        self._entries.append(item)

    def recall(self):
        return list(self._entries)
