"""Parametrized rate limit cross-key isolation."""
import pytest
from aios_core.rate_limiter import RateLimiter

@pytest.mark.parametrize("rpm,keys,per_key", [
    (1, 1, 1), (2, 2, 1), (5, 5, 1), (10, 5, 2),
])
def test_cross_key_budget(rpm, keys, per_key):
    rl = RateLimiter(requests_per_minute=rpm)
    for k in range(keys):
        for _ in range(per_key):
            assert rl.is_allowed(f"key{k}") is True

@pytest.mark.parametrize("n_calls", [0, 1, 5, 10, 50, 100])
def test_requests_under_limit(n_calls):
    rl = RateLimiter(requests_per_minute=200)
    for i in range(n_calls):
        assert rl.is_allowed(f"k{i}") is True
