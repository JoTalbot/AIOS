"""Adaptive strategy selection based on learning signals."""


class StrategyScore:
    def __init__(self, strategy_id: str, score: float = 0.0):
        self.strategy_id = strategy_id
        self.score = score


class AdaptiveStrategyEngine:
    def __init__(self):
        self.strategies = {}

    def register_strategy(self, strategy_id: str):
        self.strategies[strategy_id] = StrategyScore(strategy_id)

    def update_score(self, strategy_id: str, reward: float):
        if strategy_id not in self.strategies:
            self.register_strategy(strategy_id)
        self.strategies[strategy_id].score += reward

    def select_best(self):
        if not self.strategies:
            return None
        return max(self.strategies.values(), key=lambda item: item.score)
