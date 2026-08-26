"""Trust and strategy aware decision resolver foundation."""

from dataclasses import dataclass


@dataclass
class DecisionCandidate:
    agent_id: str
    trust_score: float
    strategy_score: float
    value: float = 0.0


class DecisionResolver:
    """Resolve decisions using trust and strategy signals."""

    def score(self, candidate: DecisionCandidate) -> float:
        return (
            candidate.trust_score * 0.5
            + candidate.strategy_score * 0.5
            + candidate.value
        )

    def select_best(self, candidates: list[DecisionCandidate]):
        if not candidates:
            return None
        return max(candidates, key=self.score)
