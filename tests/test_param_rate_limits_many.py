import pytest

from aios_core.rate_limiter import RateLimiter


@pytest.mark.parametrize("rpm", [1,2,3,5,10,20,50,100])
def test_exact_limit(rpm):
    rl = RateLimiter(requests_per_minute=rpm)
    for _ in range(rpm):
        assert rl.is_allowed("k") is True
    assert rl.is_allowed("k") is False

@pytest.mark.parametrize("keys", [1,5,10,50])
def test_independent_keys(keys):
    rl = RateLimiter(requests_per_minute=2)
    for i in range(keys):
        assert rl.is_allowed(f"k{i}") is True
