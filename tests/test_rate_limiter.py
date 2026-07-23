"""Tests for Rate Limiter"""

from aios_core.rate_limiter import RateLimiter


def test_rate_limiter_allows():
    limiter = RateLimiter(requests_per_minute=5)
    assert limiter.is_allowed("test") is True


def test_rate_limiter_blocks():
    limiter = RateLimiter(requests_per_minute=2)
    assert limiter.is_allowed("test") is True
    assert limiter.is_allowed("test") is True
    assert limiter.is_allowed("test") is False
