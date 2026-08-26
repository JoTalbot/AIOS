from dataclasses import dataclass
from typing import List


@dataclass
class ConsensusVote:
    agent_id: str
    action: str
    confidence: float
    reason: str = ""


@dataclass
class ConsensusResult:
    action: str
    confidence: float
    votes: int


class ConsensusEngine:
    """Weighted consensus engine for multi-agent decisions."""

    def decide(self, votes: List[ConsensusVote]) -> ConsensusResult:
        if not votes:
            return ConsensusResult("abort", 0.0, 0)

        scores = {}
        for vote in votes:
            scores[vote.action] = scores.get(vote.action, 0.0) + vote.confidence

        action = max(scores, key=scores.get)
        total = sum(scores.values())
        confidence = scores[action] / total if total else 0.0

        return ConsensusResult(
            action=action,
            confidence=confidence,
            votes=len(votes),
        )
