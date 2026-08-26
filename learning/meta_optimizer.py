class MetaOptimizer:
    def __init__(self):
        self.strategies = {}

    def register(self, name, score=0):
        self.strategies[name] = score

    def update(self, name, score):
        self.strategies[name] = score

    def best(self):
        if not self.strategies:
            return None
        return max(self.strategies, key=self.strategies.get)
