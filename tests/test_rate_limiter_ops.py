"""Rate limiter operations tests."""
from aios_core.rate_limiter import RateLimiter
def test_rate_limit_reset():
    rl = RateLimiter(requests_per_minute=5)
    for _ in range(5): assert rl.is_allowed("k")
    assert not rl.is_allowed("k")
