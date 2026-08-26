"""AIOS v23.8 Swarm Decision Layer.

Provides a foundation for collective agent decisions.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class DecisionProposal:
    agent_id: str
    decision: Any
    confidence: float = 0.0


class SwarmDecisionLayer:
    def __init__(self):
        self.proposals: List[DecisionProposal] = []

    def submit(self, agent_id: str, decision: Any, confidence: float = 0.0):
        proposal = DecisionProposal(agent_id, decision, confidence)
        self.proposals.append(proposal)
        return proposal

    def consensus(self):
        if not self.proposals:
            return None
        return max(self.proposals, key=lambda item: item.confidence)
