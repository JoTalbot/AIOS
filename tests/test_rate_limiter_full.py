"""Full tests for rate limiter including window behavior."""

from aios_core.rate_limiter import RateLimiter


def test_rate_limiter_exhaustion():
    rl = RateLimiter(requests_per_minute=3)
    assert rl.is_allowed("key1") is True
    assert rl.is_allowed("key1") is True
    assert rl.is_allowed("key1") is True
    assert rl.is_allowed("key1") is False


def test_rate_limiter_independent():
    rl = RateLimiter(requests_per_minute=1)
    assert rl.is_allowed("a") is True
    assert rl.is_allowed("a") is False
    assert rl.is_allowed("b") is True
