"""Tests for Rate Limiter"""

import time

from aios_core.rate_limiter import RateLimiter


def test_rate_limiter_allows():
    limiter = RateLimiter(requests_per_minute=5)
    assert limiter.is_allowed("test") is True


def test_rate_limiter_blocks():
    limiter = RateLimiter(requests_per_minute=2)
    assert limiter.is_allowed("test") is True
    assert limiter.is_allowed("test") is True
    assert limiter.is_allowed("test") is False


def test_rate_limiter_respects_window():
    limiter = RateLimiter(requests_per_minute=60)
    for _ in range(60):
        assert limiter.is_allowed("a") is True
    assert limiter.is_allowed("a") is False


def test_rate_limiter_independent_keys():
    limiter = RateLimiter(requests_per_minute=1)
    assert limiter.is_allowed("key_a") is True
    assert limiter.is_allowed("key_a") is False
    assert limiter.is_allowed("key_b") is True  # different key — not blocked
