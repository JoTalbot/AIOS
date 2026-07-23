"""Parametrized rate limit tests."""
import pytest
from aios_core.rate_limiter import RateLimiter

@pytest.mark.parametrize("rpm,allowed,denied", [
    (1, 1, 1), (2, 2, 1), (5, 5, 1), (10, 10, 1), (60, 60, 1),
])
def test_rate_limit_exact(rpm, allowed, denied):
    rl = RateLimiter(requests_per_minute=rpm)
    for _ in range(allowed): assert rl.is_allowed("k") is True
    for _ in range(denied): assert rl.is_allowed("k") is False
