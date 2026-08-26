"""Adaptive strategy selection for AIOS learning core."""


class AdaptiveStrategySelector:
    def __init__(self):
        self.strategies = {}

    def add_strategy(self, name, score=0):
        self.strategies[name] = score

    def best_strategy(self):
        if not self.strategies:
            return None
        return max(self.strategies, key=self.strategies.get)
