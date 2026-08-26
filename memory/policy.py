"""Adaptive policy layer backed by execution experience memory."""

from dataclasses import dataclass
from typing import Optional

from .recovery_memory import RecoveryMemory


@dataclass
class PolicyChoice:
    action: str
    score: float
    source: str


class AdaptivePolicy:
    """Selects actions using historical recovery experience."""

    def __init__(self, memory: Optional[RecoveryMemory] = None):
        self.memory = memory or RecoveryMemory()

    def choose(self, failure_type: str, actions: list[str]) -> PolicyChoice:
        best_action = None
        best_score = -1.0

        for action in actions:
            score = self.memory.score_action(failure_type, action)
            if score > best_score:
                best_action = action
                best_score = score

        if best_action is None:
            return PolicyChoice(
                action=actions[0] if actions else "abort",
                score=0.0,
                source="default",
            )

        return PolicyChoice(
            action=best_action,
            score=best_score,
            source="memory",
        )
