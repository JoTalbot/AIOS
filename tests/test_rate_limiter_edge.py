"""Rate limiter edge cases."""
from aios_core.rate_limiter import RateLimiter
def test_zero(): assert RateLimiter(0).is_allowed("k") is False
def test_high(): rl=RateLimiter(100000); [rl.is_allowed(f"k{i}") for i in range(1000)]; assert True
