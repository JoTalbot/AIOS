"""Consensus adapter for AIOS decision flow."""

from dataclasses import dataclass


@dataclass
class ConsensusDecision:
    action: str
    confidence: float
    source: str = "consensus"


class ConsensusAdapter:
    """Bridges multi-agent consensus results into decisions."""

    def apply(self, result):
        if not result:
            return ConsensusDecision(
                action="abort",
                confidence=0.0,
                source="fallback",
            )

        return ConsensusDecision(
            action=result.action,
            confidence=result.confidence,
        )
