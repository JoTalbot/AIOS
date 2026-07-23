"""Edge: rate limiter with extremely high requests."""
from aios_core.rate_limiter import RateLimiter

def test_high_rpm_no_panic():
    rl = RateLimiter(requests_per_minute=100000)
    for i in range(10000):
        assert rl.is_allowed(f"key_{i}") is True
    assert rl.is_allowed("single_key") is True

def test_zero_rpm_blocks_all():
    rl = RateLimiter(requests_per_minute=0)
    for i in range(100):
        assert rl.is_allowed(f"k{i}") is False
