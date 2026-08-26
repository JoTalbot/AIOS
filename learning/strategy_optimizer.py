class StrategyOptimizer:
    def __init__(self):
        self.strategies = {}

    def register(self, name, strategy):
        self.strategies[name] = {
            "strategy": strategy,
            "score": 0
        }

    def update_score(self, name, reward):
        if name in self.strategies:
            self.strategies[name]["score"] += reward

    def best(self):
        if not self.strategies:
            return None
        return max(self.strategies, key=lambda x: self.strategies[x]["score"])
