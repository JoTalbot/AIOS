from dataclasses import dataclass
from typing import Optional


@dataclass
class DecisionCandidate:
    action: str
    confidence: float
    source: str


class OptimizedDecisionResolver:
    """
    Resolves final action using consensus confidence,
    adaptive policy score and optimization score.
    """

    def resolve(
        self,
        consensus: Optional[DecisionCandidate],
        policy: Optional[DecisionCandidate],
        optimization_score: float = 0.0,
    ) -> DecisionCandidate:
        candidates = []

        if consensus:
            candidates.append(
                (
                    consensus,
                    consensus.confidence * 0.4 + optimization_score * 0.3,
                )
            )

        if policy:
            candidates.append(
                (
                    policy,
                    policy.confidence * 0.4 + optimization_score * 0.3,
                )
            )

        if not candidates:
            return DecisionCandidate(
                action="fallback",
                confidence=0.0,
                source="resolver",
            )

        return max(candidates, key=lambda item: item[1])[0]
