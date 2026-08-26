class PersistentMemoryStore:
    def __init__(self):
        self.storage = {}

    def save(self, key, value):
        self.storage[key] = value

    def load(self, key, default=None):
        return self.storage.get(key, default)
