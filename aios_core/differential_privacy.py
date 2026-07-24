"""Differential Privacy for AIOS"""

import random
from typing import List


class DifferentialPrivacy:
    """Simple differential privacy mechanisms."""

    def __init__(self, epsilon: float = 1.0):
        """Initialize DifferentialPrivacy."""
        self.epsilon = epsilon

    def add_noise(self, value: float, sensitivity: float = 1.0) -> float:
        """Laplace mechanism."""
        scale = sensitivity / self.epsilon
        noise = random.gauss(0, scale)
        return value + noise

    def privatize_list(self, values: list[float], sensitivity: float = 1.0) -> list[float]:
        """Execute privatize list."""
        return [self.add_noise(v, sensitivity) for v in values]

    def stats(self) -> dict:
        """Return statistics dict."""
        return {"epsilon": self.epsilon}
