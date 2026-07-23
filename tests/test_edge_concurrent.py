"""Edge case tests — concurrent-like patterns."""
from aios_core.rate_limiter import RateLimiter
from aios_core.cache import CacheManager

def test_rate_limiter_many_keys():
    rl = RateLimiter(requests_per_minute=100)
    for i in range(200):
        assert rl.is_allowed(f"key{i}") is True
    assert rl.is_allowed("key0") is False

def test_cache_many_ops():
    cm = CacheManager()
    for i in range(100):
        assert cm.stats() is not None
