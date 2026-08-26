"""Behavior model for comparing observed and predicted twin states."""

from dataclasses import dataclass, field
from typing import Dict


@dataclass
class BehaviorModel:
    baseline: Dict[str, float] = field(default_factory=dict)

    def observe(self, state: Dict[str, float]) -> None:
        self.baseline.update(state)

    def deviation(self, state: Dict[str, float]) -> Dict[str, float]:
        return {k: v - self.baseline[k] for k, v in state.items() if k in self.baseline}
