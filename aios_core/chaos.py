"""Chaos Engineering for AIOS"""

import random
from typing import Callable


class ChaosMonkey:
    """Simple chaos engineering toolkit."""

    def __init__(self, failure_rate: float = 0.1):
        self.failure_rate = failure_rate

    def maybe_fail(self) -> None:
        """Execute maybe fail."""
        if random.random() < self.failure_rate:
            raise Exception("ChaosMonkey injected failure")

    def wrap(self, func: Callable) -> None:
        """Execute wrap."""
        def wrapper(*args, **kwargs) -> None:
            """Execute wrapper."""
            self.maybe_fail()
            return func(*args, **kwargs)

        return wrapper

    def stats(self) -> dict:
        """Return statistics dict."""
        return {"failure_rate": self.failure_rate}


chaos = ChaosMonkey(failure_rate=0.05)
