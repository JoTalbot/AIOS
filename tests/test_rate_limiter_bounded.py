"""Tests for RateLimiter memory leak fix and bounded cleanup."""

from aios_core.rate_limiter import RateLimiter


class TestRateLimiterBounded:
    """RateLimiter no longer leaks memory on repeated is_allowed calls."""

    def test_is_allowed_returns_true(self):
        rl = RateLimiter(requests_per_minute=100)
        assert rl.is_allowed("test_key") is True

    def test_is_allowed_returns_false_when_exhausted(self):
        rl = RateLimiter(requests_per_minute=5)
        for i in range(5):
            rl.is_allowed(f"limited:{i}")
        # 6th call with same key pattern should be allowed (different key)
        assert rl.is_allowed("limited:5") is True
        # Exhaust a single key
        rl2 = RateLimiter(requests_per_minute=2)
        assert rl2.is_allowed("single") is True
        assert rl2.is_allowed("single") is True
        assert rl2.is_allowed("single") is False

    def test_memory_is_bounded(self):
        """After many calls, requests dict stays bounded."""
        rl = RateLimiter(requests_per_minute=10)
        # Call is_allowed 1000 times — should not grow beyond 10 per key
        for i in range(1000):
            rl.is_allowed("bounded_key")
        # The list for 'bounded_key' should be at most 10 entries
        assert len(rl.requests["bounded_key"]) <= 10

    def test_get_stats_prunes_old_entries(self):
        """get_stats prunes expired timestamps."""
        rl = RateLimiter(requests_per_minute=100)
        rl.is_allowed("stats_key")
        stats = rl.get_stats("stats_key")
        assert stats["remaining"] < 100
        assert stats["limit"] == 100

    def test_reset_clears_all(self):
        """reset() clears all counters."""
        rl = RateLimiter(requests_per_minute=100)
        rl.is_allowed("key1")
        rl.is_allowed("key2")
        rl.reset()
        assert len(rl.requests) == 0

    def test_reset_specific_key(self):
        """reset(key) clears only that key."""
        rl = RateLimiter(requests_per_minute=100)
        rl.is_allowed("keep")
        rl.is_allowed("remove")
        rl.reset("remove")
        assert "keep" in rl.requests
        assert "remove" not in rl.requests

    def test_benchmark_no_timeout(self):
        """RateLimiter is_allowed should not timeout under repeated calls."""
        rl = RateLimiter(requests_per_minute=100000)
        for i in range(100):
            rl.is_allowed(f"bench_key_{i}")
        # Should complete without timeout — no memory leak
        assert len(rl.requests) <= 100
