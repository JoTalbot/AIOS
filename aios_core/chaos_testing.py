"""Chaos Testing Framework for AIOS"""

import random
from typing import Callable, Dict


class ChaosTester:
    """Injects failures and latency for resilience testing."""

    def __init__(self, failure_probability: float = 0.1, latency_ms: int = 0):
        self.failure_probability = failure_probability
        self.latency_ms = latency_ms

    def inject(self, func: Callable) -> None:
        """Execute inject."""
        def wrapper(*args, **kwargs) -> None:
            """Execute wrapper."""
            if random.random() < self.failure_probability:
                raise Exception("Chaos injection: simulated failure")
            if self.latency_ms > 0:
                import time

                time.sleep(self.latency_ms / 1000)
            return func(*args, **kwargs)

        return wrapper

    def stats(self) -> dict:
        """Return statistics dict."""
        return {
            "failure_probability": self.failure_probability,
            "latency_ms": self.latency_ms,
        }
