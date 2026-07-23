"""Edge: rate limiter many keys."""
from aios_core.rate_limiter import RateLimiter
def test_many_keys():
    rl = RateLimiter(requests_per_minute=1000)
    for i in range(10000):
        assert rl.is_allowed(f"k{i}") is True
