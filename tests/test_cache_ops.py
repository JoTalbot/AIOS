"""Cache operations tests."""
from aios_core.cache import CacheManager
def test_cache_ops():
    cm = CacheManager()
    assert cm.stats() is not None
