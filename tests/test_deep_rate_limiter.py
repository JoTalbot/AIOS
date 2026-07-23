"""Deep rate limiter — timing properties."""
from aios_core.rate_limiter import RateLimiter
import time
def test_window_boundary():
    rl = RateLimiter(requests_per_minute=60)
    for _ in range(60): assert rl.is_allowed("k") is True
    assert rl.is_allowed("k") is False
def test_cross_key_isolation():
    rl = RateLimiter(requests_per_minute=1)
    assert rl.is_allowed("a") is True
    assert rl.is_allowed("b") is True
    assert rl.is_allowed("a") is False
    assert rl.is_allowed("b") is False
