class MemoryManager:
    def __init__(self, short_term, long_term, vector):
        self.short_term = short_term
        self.long_term = long_term
        self.vector = vector

    def remember(self, item):
        self.short_term.remember(item)

    def store(self, key, value):
        self.long_term.save(key, value)
