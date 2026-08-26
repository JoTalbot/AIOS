from dataclasses import dataclass
from typing import Any


@dataclass
class PolicyStrategyContext:
    strategy: str
    context: Any = None


class PolicyStrategyIntegration:
    def __init__(self, strategy_engine):
        self.strategy_engine = strategy_engine

    def select_strategy(self, available_strategies):
        return self.strategy_engine.select_best(available_strategies)

    def build_context(self, strategy, context=None):
        return PolicyStrategyContext(strategy=strategy, context=context)
