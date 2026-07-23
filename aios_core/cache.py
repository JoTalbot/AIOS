"""Simple In-Memory Cache for AIOS"""

import time
from typing import Any, Dict, Optional


class TTLCache:
    """Time-To-Live cache."""

    def __init__(self, default_ttl: int = 300):
        self.default_ttl = default_ttl
        self._store: Dict[str, tuple] = {}  # key -> (value, expiry)

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Execute set."""
        expiry = time.time() + (ttl or self.default_ttl)
        self._store[key] = (value, expiry)

    def get(self, key: str) -> Optional[Any]:
        """Execute get."""
        if key not in self._store:
            return None
        value, expiry = self._store[key]
        if time.time() > expiry:
            del self._store[key]
            return None
        return value

    def delete(self, key: str) -> None:
        """Execute delete."""
        self._store.pop(key, None)

    def clear(self) -> None:
        """Execute clear."""
        self._store.clear()

    def stats(self) -> dict:
        """Return statistics dict."""
        return {"size": len(self._store), "default_ttl": self.default_ttl}


cache = TTLCache()
