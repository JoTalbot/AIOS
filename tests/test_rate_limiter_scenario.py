"""test_rate_limiter_scenario test."""
from aios_core.rate_limiter import RateLimiter


def test_window_isolation():
    rl = RateLimiter(requests_per_minute=2)
    assert rl.is_allowed("a") is True
    assert rl.is_allowed("b") is True
    assert rl.is_allowed("a") is True
    assert rl.is_allowed("a") is False
    assert rl.is_allowed("b") is True
