"""Parametrized tests for Rate Limiter."""

import pytest
from aios_core.rate_limiter import RateLimiter


@pytest.mark.parametrize("rpm,allowed_count", [
    (1, 1), (2, 2), (5, 5), (10, 10), (60, 60),
])
def test_rate_limiter_limits(rpm, allowed_count):
    rl = RateLimiter(requests_per_minute=rpm)
    for _ in range(allowed_count):
        assert rl.is_allowed("test") is True
    assert rl.is_allowed("test") is False
