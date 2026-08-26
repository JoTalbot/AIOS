"""Long-term strategy memory for AIOS agents."""

from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass
class StrategyMemory:
    strategies: List[Dict[str, Any]] = field(default_factory=list)

    def store(self, strategy: Dict[str, Any]) -> None:
        self.strategies.append(strategy)

    def best(self) -> Dict[str, Any] | None:
        if not self.strategies:
            return None
        return max(self.strategies, key=lambda item: item.get("score", 0))
