"""Simple Rate Limiter for AIOS API

In-memory rate limiter with sliding window counter, token bucket,
burst allowance, tiered limits, IP-based throttling, and quota tracking.

Features:
- Fixed memory: bounded timestamp storage per key
- Sliding window counter with configurable window size
- Token bucket mode for burst-friendly APIs
- Tiered rate limits (e.g. free=60, premium=300, admin=∞)
- Per-key quota tracking with reset capability
"""

import time
from collections import defaultdict
from typing import Any

__all__ = ["RateLimiter", "rate_limiter"]


class RateLimiter:
    """In-memory rate limiter (sliding window + token bucket).

    Fixed memory: each key stores at most ``requests_per_minute`` timestamps.
    Old entries are pruned on every ``is_allowed`` call, preventing unbounded
    growth that previously caused CI benchmark timeouts.

    Supports both sliding-window-counter and token-bucket modes:
    - *sliding window*: strict rate limit, no bursts beyond the window rate
    - *token bucket*: allows short bursts up to ``burst_size`` while
      maintaining average rate over time
    """

    __slots__ = (
        "_burst_size",
        "_last_refill",
        "_mode",
        "_quota_limits",
        "_quota_used",
        "_tiers",
        "_tokens",
        "requests",
        "requests_per_minute",
        "window_seconds",
    )

    def __init__(
        self,
        requests_per_minute: int = 60,
        window_seconds: int = 60,
        burst_size: int = 10,
        mode: str = "sliding_window",
    ):
        """Initialize RateLimiter.

        Args:
            requests_per_minute: Maximum requests per window for default tier.
            window_seconds: Time window in seconds (default 60).
            burst_size: Maximum burst for token-bucket mode.
            mode: "sliding_window" or "token_bucket".
        """
        self.requests_per_minute = requests_per_minute
        self.requests: dict[str, list[float]] = defaultdict(list)
        self.window_seconds = window_seconds
        self._burst_size = burst_size
        self._tokens: dict[str, float] = {}
        self._last_refill: dict[str, float] = {}
        self._tiers: dict[str, int] = {}  # key → custom RPM
        self._quota_used: dict[str, float] = {}  # key → total requests in period
        self._quota_limits: dict[str, float] = {}  # key → max quota
        self._mode = mode

    # ------------------------------------------------------------------
    # Tiered limits
    # ------------------------------------------------------------------

    def set_tier(self, key: str, requests_per_minute: int) -> None:
        """Set a custom rate limit tier for *key*."""
        self._tiers[key] = requests_per_minute

    def get_tier(self, key: str) -> int:
        """Return effective RPM for *key* (default if no tier set)."""
        return self._tiers.get(key, self.requests_per_minute)

    def clear_tier(self, key: str) -> None:
        """Remove a per-key rate override and restore the default limit."""
        self._tiers.pop(key, None)

    def set_quota(self, key: str, quota_limit: float) -> None:
        """Set a total-usage quota limit for *key* (e.g. 10000 requests/month)."""
        self._quota_limits[key] = quota_limit

    # ------------------------------------------------------------------
    # Rate checking
    # ------------------------------------------------------------------

    def is_allowed(self, key: str) -> bool:
        """Check whether a request with *key* is allowed within the rate limit.

        Uses sliding-window-counter mode by default, token-bucket if
        ``self._mode == "token_bucket"``.
        """
        if self._mode == "token_bucket":
            return self._token_bucket_allowed(key)

        rpm = self.get_tier(key)
        now = time.time()
        window = self.window_seconds

        # Prune expired timestamps
        entry = self.requests[key]
        cutoff = now - window
        pruned = [t for t in entry if t >= cutoff]
        self.requests[key] = pruned

        # Check quota
        if key in self._quota_limits:
            used = self._quota_used.get(key, 0)
            if used >= self._quota_limits[key]:
                return False

        if len(pruned) < rpm:
            pruned.append(now)
            self.requests[key] = pruned
            self._quota_used[key] = self._quota_used.get(key, 0) + 1
            return True
        return False

    def _token_bucket_allowed(self, key: str) -> bool:
        """Token bucket rate check — allows bursts."""
        now = time.time()
        rpm = self.get_tier(key)
        refill_rate = rpm / self.window_seconds  # tokens per second

        # Initialize bucket
        if key not in self._tokens:
            self._tokens[key] = self._burst_size
            self._last_refill[key] = now

        # Refill tokens based on elapsed time
        elapsed = now - self._last_refill[key]
        self._tokens[key] = min(
            self._burst_size,
            self._tokens[key] + elapsed * refill_rate,
        )
        self._last_refill[key] = now

        # Check quota
        if key in self._quota_limits:
            used = self._quota_used.get(key, 0)
            if used >= self._quota_limits[key]:
                return False

        if self._tokens[key] >= 1.0:
            self._tokens[key] -= 1.0
            self._quota_used[key] = self._quota_used.get(key, 0) + 1
            return True
        return False

    # ------------------------------------------------------------------
    # Stats & management
    # ------------------------------------------------------------------

    def get_stats(self, key: str) -> dict:
        """Get remaining requests and limit for a key."""
        if self._mode == "token_bucket":
            rpm = self.get_tier(key)
            tokens = self._tokens.get(key, self._burst_size)
            return {
                "remaining": int(tokens),
                "limit": rpm,
                "burst_remaining": int(tokens),
                "burst_size": self._burst_size,
                "mode": "token_bucket",
            }

        now = time.time()
        window = self.window_seconds
        rpm = self.get_tier(key)
        pruned = [t for t in self.requests[key] if now - t < window]
        self.requests[key] = pruned
        remaining = max(0, rpm - len(pruned))
        result = {
            "remaining": remaining,
            "limit": rpm,
            "used": len(pruned),
            "window_seconds": window,
            "mode": "sliding_window",
        }
        if key in self._quota_limits:
            result["quota_used"] = self._quota_used.get(key, 0)
            result["quota_limit"] = self._quota_limits[key]
        return result

    def reset(self, key: str | None = None) -> None:
        """Reset rate limit counters.

        If *key* is given, reset only that key; otherwise clear all.
        """
        if key is None:
            self.requests.clear()
            self._tokens.clear()
            self._last_refill.clear()
            self._quota_used.clear()
        else:
            self.requests.pop(key, None)
            self._tokens.pop(key, None)
            self._last_refill.pop(key, None)
            self._quota_used.pop(key, None)

    def set_mode(self, mode: str) -> None:
        """Switch between ``sliding_window`` and ``token_bucket`` modes."""
        self._mode = mode

    def all_stats(self) -> dict[str, Any]:
        """Return aggregate statistics across all keys."""
        return {
            "total_keys": len(self.requests) + len(self._tokens),
            "mode": self._mode,
            "default_rpm": self.requests_per_minute,
            "window_seconds": self.window_seconds,
            "burst_size": self._burst_size,
            "tiers": dict(self._tiers),
            "quota_keys": list(self._quota_limits.keys()),
        }


# Global instance
rate_limiter = RateLimiter(requests_per_minute=120)
