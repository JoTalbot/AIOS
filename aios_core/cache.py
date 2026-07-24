"""Simple In-Memory Cache for AIOS v10.8.0.

TTL cache with LRU eviction, size limits, namespace
support, hit/miss statistics, cache warming, and
event callbacks.

Classes:
    CacheEntry     — cached entry with metadata
    TTLCache       — full TTL cache engine
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Cached entry with metadata."""

    key: str
    value: Any
    expiry: float
    namespace: str = "default"
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    access_count: int = 0
    size_bytes: int = 0


class TTLCache:
    """Full TTL cache engine.

    Features:
    - Time-To-Live (TTL) expiration
    - LRU (Least Recently Used) eviction
    - Size limits (max entries)
    - Namespace support (isolated key spaces)
    - Hit/miss statistics tracking
    - Cache warming (pre-fill)
    - Event callbacks (on_evict, on_expire)
    - Bulk operations
    """

    def __init__(self, default_ttl: int = 300, max_size: int = 10000) -> None:
        self.default_ttl = default_ttl
        self.max_size = max_size
        self._store: dict[str, CacheEntry] = {}
        self._namespaces: dict[str, dict[str, CacheEntry]] = {}
        self._hits: int = 0
        self._misses: int = 0
        self._evictions: int = 0
        self._expirations: int = 0
        self._on_evict: Callable | None = None
        self._on_expire: Callable | None = None

    # ── Core Operations ─────────────────────────────────────────────

    def set(
        self, key: str, value: Any, ttl: int | None = None, namespace: str = "default"
    ) -> None:
        """Set a cache entry with optional TTL and namespace."""
        expiry = time.time() + (ttl or self.default_ttl)

        # Estimate size
        size = len(str(value)) if value else 0

        entry = CacheEntry(
            key=key,
            value=value,
            expiry=expiry,
            namespace=namespace,
            size_bytes=size,
        )
        self._store[key] = entry

        # Namespace tracking
        if namespace not in self._namespaces:
            self._namespaces[namespace] = {}
        self._namespaces[namespace][key] = entry

        # Check size limit and evict if needed
        self._evict_if_needed()

    def get(self, key: str, namespace: str | None = None) -> Any | None:
        """Get a cache entry, returning None if expired or missing."""
        entry = self._store.get(key)
        if entry is None:
            self._misses += 1
            return None

        # Check namespace
        if namespace and entry.namespace != namespace:
            self._misses += 1
            return None

        # Check expiration
        if time.time() > entry.expiry:
            self._expirations += 1
            self._remove_entry(key)
            if self._on_expire:
                self._on_expire(key, entry.value)
            self._misses += 1
            return None

        # Update access stats (LRU tracking)
        entry.last_accessed = time.time()
        entry.access_count += 1
        self._hits += 1
        return entry.value

    def has(self, key: str) -> bool:
        """Check if key exists and is not expired."""
        entry = self._store.get(key)
        if entry is None:
            return False
        return time.time() <= entry.expiry

    def delete(self, key: str) -> None:
        """Delete a cache entry."""
        self._remove_entry(key)

    def clear(self) -> None:
        """Clear all cache entries."""
        self._store.clear()
        self._namespaces.clear()

    def clear_namespace(self, namespace: str) -> None:
        """Clear all entries in a namespace."""
        ns = self._namespaces.get(namespace, {})
        for key in ns:
            self._store.pop(key, None)
        self._namespaces.pop(namespace, None)

    # ── Internal ────────────────────────────────────────────────────

    def _remove_entry(self, key: str) -> None:
        """Remove entry from store and namespace."""
        entry = self._store.pop(key, None)
        if entry:
            ns = self._namespaces.get(entry.namespace)
            if ns:
                ns.pop(key, None)

    def _evict_if_needed(self) -> None:
        """Evict LRU entries if size limit exceeded."""
        while len(self._store) > self.max_size:
            # Find LRU entry (least recently accessed)
            lru_key = min(self._store, key=lambda k: self._store[k].last_accessed)
            entry = self._store[lru_key]
            self._evictions += 1
            if self._on_evict:
                self._on_evict(lru_key, entry.value)
            self._remove_entry(lru_key)

    def _purge_expired(self) -> int:
        """Remove all expired entries."""
        now = time.time()
        expired_keys = [k for k, e in self._store.items() if now > e.expiry]
        for key in expired_keys:
            entry = self._store.get(key)
            if entry and self._on_expire:
                self._on_expire(key, entry.value)
            self._remove_entry(key)
            self._expirations += 1
        return len(expired_keys)

    # ── Bulk Operations ──────────────────────────────────────────────

    def set_many(
        self, items: dict[str, Any], ttl: int | None = None, namespace: str = "default"
    ) -> None:
        """Set multiple cache entries."""
        for key, value in items.items():
            self.set(key, value, ttl, namespace)

    def get_many(self, keys: list[str]) -> dict[str, Any]:
        """Get multiple cache entries."""
        result = {}
        for key in keys:
            val = self.get(key)
            if val is not None:
                result[key] = val
        return result

    # ── Cache Warming ────────────────────────────────────────────────

    def warm(self, data: dict[str, Any], ttl: int | None = None) -> None:
        """Pre-fill cache with data (cache warming)."""
        self.set_many(data, ttl)

    # ── Event Callbacks ──────────────────────────────────────────────

    def on_evict(self, callback: Callable) -> None:
        """Set callback for eviction events."""
        self._on_evict = callback

    def on_expire(self, callback: Callable) -> None:
        """Set callback for expiration events."""
        self._on_expire = callback

    # ── Stats ──────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        """Return cache statistics."""
        total = self._hits + self._misses
        hit_rate = self._hits / total if total > 0 else 0.0
        self._purge_expired()

        return {
            "size": len(self._store),
            "default_ttl": self.default_ttl,
            "max_size": self.max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(hit_rate, 4),
            "evictions": self._evictions,
            "expirations": self._expirations,
            "namespaces": len(self._namespaces),
        }


cache = TTLCache()
