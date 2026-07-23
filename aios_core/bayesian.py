"""Bayesian Inference for AIOS"""

import random
from typing import Any, Dict


class BayesianInference:
    """Simple Bayesian belief updating."""

    def __init__(self):
        self.beliefs: Dict[str, float] = {}

    def update_belief(self, hypothesis: str, evidence: bool, likelihood: float = 0.8) -> None:
        """Execute update belief."""
        prior = self.beliefs.get(hypothesis, 0.5)
        if evidence:
            posterior = (likelihood * prior) / (likelihood * prior + (1 - likelihood) * (1 - prior))
        else:
            posterior = ((1 - likelihood) * prior) / (
                (1 - likelihood) * prior + likelihood * (1 - prior)
            )
        self.beliefs[hypothesis] = round(posterior, 4)

    def get_belief(self, hypothesis: str) -> float:
        """Execute get belief."""
        return self.beliefs.get(hypothesis, 0.5)

    def stats(self) -> dict:
        """Return statistics dict."""
        return {"hypotheses": len(self.beliefs)}
