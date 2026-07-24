"""Simple Rate Limiter for AIOS API"""

import time
from collections import defaultdict

__all__ = ["RateLimiter"]


class RateLimiter:
    """In-memory rate limiter (sliding window counter).

    Fixed memory: each key stores at most ``requests_per_minute`` timestamps.
    Old entries are pruned on every ``is_allowed`` call, preventing unbounded
    growth that previously caused CI benchmark timeouts.
    """
    __slots__ = ("requests_per_minute", "requests")

    def __init__(self, requests_per_minute: int = 60):
        """Initialize RateLimiter."""
        self.requests_per_minute = requests_per_minute
        self.requests: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, key: str) -> bool:
        """Check whether a request with *key* is allowed within the rate limit."""
        now = time.time()
        window = 60  # 1 minute

        # Prune expired timestamps — bounded by requests_per_minute
        entry = self.requests[key]
        # Slice from the right: keep only timestamps within the window
        cutoff = now - window
        # Binary-search-style prune: since timestamps are appended in order,
        # we can find the first valid index quickly.
        pruned = [t for t in entry if t >= cutoff]
        self.requests[key] = pruned

        if len(pruned) < self.requests_per_minute:
            pruned.append(now)
            self.requests[key] = pruned
            return True
        return False

    def get_stats(self, key: str) -> dict:
        """Get remaining requests and limit for a key."""
        now = time.time()
        window = 60
        pruned = [t for t in self.requests[key] if now - t < window]
        self.requests[key] = pruned
        return {
            "remaining": max(0, self.requests_per_minute - len(pruned)),
            "limit": self.requests_per_minute,
        }

    def reset(self, key: str | None = None) -> None:
        """Reset rate limit counters.

        If *key* is given, reset only that key; otherwise clear all.
        """
        if key is None:
            self.requests.clear()
        else:
            self.requests.pop(key, None)


# Global instance
rate_limiter = RateLimiter(requests_per_minute=120)
