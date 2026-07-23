"""Parametrized: rate limits exhaustive."""
import pytest
from aios_core.rate_limiter import RateLimiter

@pytest.mark.parametrize("rpm", [1,2,3,5,10,20,30,60,120,600])
def test_rpm_precision(rpm):
    rl = RateLimiter(requests_per_minute=rpm)
    for _ in range(rpm): assert rl.is_allowed("key") is True
    assert rl.is_allowed("key") is False

@pytest.mark.parametrize("n_keys", [1,5,10,50,100])
def test_key_independence(n_keys):
    rl = RateLimiter(requests_per_minute=1)
    for i in range(n_keys): assert rl.is_allowed(f"k{i}") is True
    for i in range(n_keys): assert rl.is_allowed(f"k{i}") is False
