"""Adaptive policy integration for AIOS decisions.

Connects historical recovery experience with decision selection.
"""

from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class PolicyDecision:
    action: str
    confidence: float
    source: str


class PolicyDecisionPipeline:
    """Combines runtime context with adaptive policy suggestions."""

    def __init__(self, policy: Optional[Any] = None):
        self.policy = policy

    def evaluate(self, context: dict) -> PolicyDecision:
        if self.policy is None:
            return PolicyDecision(
                action="continue",
                confidence=0.5,
                source="default",
            )

        choice = self.policy.choose(context)

        return PolicyDecision(
            action=getattr(choice, "action", "continue"),
            confidence=getattr(choice, "confidence", 0.5),
            source="adaptive_policy",
        )
