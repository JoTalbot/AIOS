"""A/B Testing Framework for AIOS"""

import random
from typing import Any, Dict


class ABTest:
    """Simple A/B testing framework."""

    def __init__(self, name: str, variants: Dict[str, float]):
        self.name = name
        self.variants = variants  # variant_name -> weight
        self.results: Dict[str, int] = {v: 0 for v in variants}

    def assign_variant(self, user_id: str) -> str:
        r = random.random()
        cumulative = 0
        for variant, weight in self.variants.items():
            cumulative += weight
            if r <= cumulative:
                return variant
        return list(self.variants.keys())[0]

    def record_result(self, variant: str, success: bool):
        if success:
            self.results[variant] = self.results.get(variant, 0) + 1

    def get_winner(self) -> str:
        return max(self.results, key=self.results.get)

    def stats(self) -> dict:
        return {"name": self.name, "results": self.results}
