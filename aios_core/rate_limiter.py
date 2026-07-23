"""Simple Rate Limiter for AIOS API"""

import time
from collections import defaultdict
from typing import Dict

__all__ = ["RateLimiter"]


class RateLimiter:
    """In-memory rate limiter (token bucket style)."""

    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.requests: Dict[str, list] = defaultdict(list)

    def is_allowed(self, key: str) -> bool:
        now = time.time()
        window = 60  # 1 minute

        # Clean old requests
        self.requests[key] = [t for t in self.requests[key] if now - t < window]

        if len(self.requests[key]) < self.requests_per_minute:
            self.requests[key].append(now)
            return True
        return False

    def get_stats(self, key: str) -> dict:
        return {
            "remaining": max(0, self.requests_per_minute - len(self.requests[key])),
            "limit": self.requests_per_minute,
        }


# Global instance
rate_limiter = RateLimiter(requests_per_minute=120)
