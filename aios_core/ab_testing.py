"""A/B Testing Framework for AIOS"""

import random
from typing import Any, Dict

__all__ = ["ABTest"]


class ABTest:
    """Simple A/B testing framework.
    __slots__ = ('name', 'variants', 'results')

    Splits traffic across weighted variants and records success/failure
    results to determine a statistical winner.
    """

    def __init__(self, name: str, variants: Dict[str, float]):
        self.name = name
        self.variants = variants  # variant_name -> weight
        self.results: Dict[str, int] = {v: 0 for v in variants}

    def assign_variant(self, user_id: str) -> str:
        """Assign *user_id* to a variant using weighted random selection."""
        r = random.random()
        cumulative = 0
        for variant, weight in self.variants.items():
            cumulative += weight
            if r <= cumulative:
                return variant
        return list(self.variants.keys())[0]

    def record_result(self, variant: str, success: bool) -> None:
        """Record a success outcome for *variant*."""
        if success:
            self.results[variant] = self.results.get(variant, 0) + 1

    def get_winner(self) -> str:
        """Return the variant with the most recorded successes."""
        return max(self.results, key=self.results.get)

    def stats(self) -> dict:
        """Return test name and per-variant results."""
        return {"name": self.name, "results": self.results}
