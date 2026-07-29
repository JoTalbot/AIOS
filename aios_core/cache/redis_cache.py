import hashlib
import json
import os
from collections.abc import Callable
from functools import wraps
from typing import Any


class RedisCache:
    def __init__(self):
        self.redis = None
        self.default_ttl = int(os.getenv("CACHE_TTL", "300"))

    async def connect(self):
        try:
            import redis.asyncio as aioredis
            self.redis = aioredis.from_url(
                os.getenv("REDIS_URL", "redis://localhost:6379"),
                decode_responses=True
            )
            await self.redis.ping()
            print("[Cache] Redis connected")
        except Exception as e:
            print(f"[Cache] Redis not available: {e}")
            self.redis = None

    async def get(self, key: str) -> Any:
        if not self.redis:
            return None
        try:
            val = await self.redis.get(f"aios:{key}")
            return json.loads(val) if val else None
        except Exception:
            return None

    async def set(self, key: str, value: Any, ttl: int = None):
        if not self.redis:
            return
        try:
            await self.redis.setex(f"aios:{key}", ttl or self.default_ttl, json.dumps(value, default=str))
        except Exception as e:
            print(f"[Cache] Set error: {e}")

    async def delete(self, key: str):
        if not self.redis:
            return
        try:
            await self.redis.delete(f"aios:{key}")
        except Exception:
            pass

    async def invalidate_pattern(self, pattern: str):
        if not self.redis:
            return
        try:
            keys = await self.redis.keys(f"aios:{pattern}")
            if keys:
                await self.redis.delete(*keys)
        except Exception:
            pass

cache = RedisCache()

def cached(key_prefix: str, ttl: int = 300):
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            key_data = f"{key_prefix}:{args}:{sorted(kwargs.items())}"
            key_hash = hashlib.md5(key_data.encode()).hexdigest()
            cached_val = await cache.get(key_hash)
            if cached_val is not None:
                return cached_val
            result = await func(*args, **kwargs)
            await cache.set(key_hash, result, ttl)
            return result
        return wrapper
    return decorator
