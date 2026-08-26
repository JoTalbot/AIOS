from abc import ABC, abstractmethod

class MemoryBackend(ABC):
    @abstractmethod
    def save(self, key, value):
        pass

    @abstractmethod
    def load(self, key):
        pass

class InMemoryBackend(MemoryBackend):
    def __init__(self):
        self.store = {}

    def save(self, key, value):
        self.store[key] = value

    def load(self, key):
        return self.store.get(key)
