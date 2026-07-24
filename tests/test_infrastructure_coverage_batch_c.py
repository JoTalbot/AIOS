"""Coverage for cache, encryption, queue and shutdown infrastructure."""

import time

from aios_core.cache import TTLCache
from aios_core.encryption import EncryptionManager
from aios_core.graceful_shutdown import GracefulShutdown, ShutdownPhase


def test_ttl_cache_namespaces_eviction_expiry_callbacks_and_bulk():
    evicted, expired = [], []
    cache = TTLCache(default_ttl=10, max_size=2)
    cache.on_evict(lambda key, value: evicted.append((key, value)))
    cache.on_expire(lambda key, value: expired.append((key, value)))
    cache.set("a", 1, namespace="one")
    assert cache.get("a", "one") == 1
    assert cache.get("a", "two") is None
    cache.set_many({"b": 2, "c": 3})
    assert evicted  # LRU eviction invokes the callback
    cache.set("short", "x", ttl=-1)
    assert cache.get("short") is None and expired
    cache.warm({"x": 1, "y": 2})
    assert cache.get_many(["x", "missing"])["x"] == 1
    cache.clear_namespace("one")
    assert cache.stats()["misses"] >= 2
    cache.clear()
    assert cache.stats()["size"] == 0


def test_encryption_roundtrip_hash_hmac_derivation_and_rotation():
    manager = EncryptionManager()
    token = manager.encrypt("private")
    assert manager.decrypt(token) == "private"
    digest, salt = manager.hash_with_salt("value", "salt")
    assert salt == "salt" and manager.verify_hash("value", digest, salt)
    signature = manager.hmac_sign("payload")
    assert manager.hmac_verify("payload", signature)
    assert not manager.hmac_verify("other", signature)
    assert len(manager.derive_key("password", salt=b"0" * 16, iterations=10)) == 32
    old = manager.get_key()
    manager.rotate_key()
    assert manager.get_key() != old and manager.stats()["rotations"] == 1


def test_graceful_shutdown_orders_phases_priorities_and_captures_failure():
    order = []
    shutdown = GracefulShutdown()
    shutdown.register_hook("cleanup-last", lambda: order.append("cleanup-last"), priority=20)
    shutdown.register_hook("cleanup-first", lambda: order.append("cleanup-first"), priority=10)
    shutdown.register_hook("drain", lambda: order.append("drain"), phase=ShutdownPhase.DRAIN)
    shutdown.register_hook("bad", lambda: 1 / 0, phase=ShutdownPhase.FINALIZE)
    result = shutdown.shutdown()
    assert result["status"] == "completed"
    assert order == ["drain", "cleanup-first", "cleanup-last"]
    assert any(item["status"] == "failed" for item in result["progress"])
    assert shutdown.shutdown()["status"] == "already_started"
    assert shutdown.stats()["shutdown_completed"]
