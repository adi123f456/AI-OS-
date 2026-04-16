"""
AI OS — Redis Client Service
Manages Redis connection for rate limiting, caching, and sessions.
Falls back to in-memory dict when Redis is not available.
"""

import json
import time
from typing import Optional, Any, Dict
from datetime import datetime


class InMemoryCache:
    """Fallback when Redis is not available."""

    def __init__(self):
        self._store: Dict[str, Dict[str, Any]] = {}

    async def get(self, key: str) -> Optional[str]:
        entry = self._store.get(key)
        if entry and (entry["expiry"] is None or entry["expiry"] > time.time()):
            return entry["value"]
        if entry:
            del self._store[key]
        return None

    async def set(self, key: str, value: str, ex: int = None):
        expiry = time.time() + ex if ex else None
        self._store[key] = {"value": value, "expiry": expiry}

    async def incr(self, key: str) -> int:
        current = await self.get(key)
        new_val = int(current or 0) + 1
        expiry = self._store.get(key, {}).get("expiry")
        self._store[key] = {"value": str(new_val), "expiry": expiry}
        return new_val

    async def expire(self, key: str, seconds: int):
        if key in self._store:
            self._store[key]["expiry"] = time.time() + seconds

    async def delete(self, key: str):
        self._store.pop(key, None)

    async def ttl(self, key: str) -> int:
        entry = self._store.get(key)
        if entry and entry["expiry"]:
            remaining = int(entry["expiry"] - time.time())
            return max(0, remaining)
        return -1

    async def exists(self, key: str) -> bool:
        return await self.get(key) is not None


class RedisService:
    """
    Redis service for rate limiting, caching, and session management.
    Falls back to in-memory cache if Redis is not available.
    """

    def __init__(self):
        self.client = None
        self.fallback = None
        self.is_connected = False

    async def initialize(self, redis_url: str = "redis://localhost:6379/0"):
        """Initialize Redis connection."""
        try:
            import redis.asyncio as aioredis
            self.client = aioredis.from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=3,
                socket_timeout=3,
            )
            # Test connection
            await self.client.ping()
            self.is_connected = True
            print("[OK] Connected to Redis")
        except Exception as e:
            print(f"[WARN] Redis connection failed: {e}")
            print("[>>] Using in-memory cache")
            self.client = None
            self.fallback = InMemoryCache()

    async def get(self, key: str) -> Optional[str]:
        if self.client:
            return await self.client.get(key)
        return await self.fallback.get(key)

    async def set(self, key: str, value: str, ex: int = None):
        if self.client:
            await self.client.set(key, value, ex=ex)
        else:
            await self.fallback.set(key, value, ex=ex)

    async def incr(self, key: str) -> int:
        if self.client:
            return await self.client.incr(key)
        return await self.fallback.incr(key)

    async def expire(self, key: str, seconds: int):
        if self.client:
            await self.client.expire(key, seconds)
        else:
            await self.fallback.expire(key, seconds)

    async def delete(self, key: str):
        if self.client:
            await self.client.delete(key)
        else:
            await self.fallback.delete(key)

    async def ttl(self, key: str) -> int:
        if self.client:
            return await self.client.ttl(key)
        return await self.fallback.ttl(key)

    async def exists(self, key: str) -> bool:
        if self.client:
            return await self.client.exists(key) > 0
        return await self.fallback.exists(key)

    # ── Rate Limiting Helpers ───────────────────────────────────────

    async def check_rate_limit(self, user_id: str, window_seconds: int, max_requests: int) -> dict:
        """
        Sliding window rate limit check.
        Returns: {"allowed": bool, "remaining": int, "reset_in": int}
        """
        key = f"ratelimit:{user_id}:{window_seconds}"
        current = await self.get(key)

        if current is None:
            await self.set(key, "1", ex=window_seconds)
            return {"allowed": True, "remaining": max_requests - 1, "reset_in": window_seconds}

        count = int(current)
        if count >= max_requests:
            reset_in = await self.ttl(key)
            return {"allowed": False, "remaining": 0, "reset_in": max(0, reset_in)}

        await self.incr(key)
        return {"allowed": True, "remaining": max_requests - count - 1, "reset_in": await self.ttl(key)}

    # ── Caching Helpers ─────────────────────────────────────────────

    async def cache_response(self, cache_key: str, response: dict, ttl: int = 300):
        """Cache an AI response for reuse."""
        await self.set(f"cache:{cache_key}", json.dumps(response), ex=ttl)

    async def get_cached_response(self, cache_key: str) -> Optional[dict]:
        """Retrieve a cached AI response."""
        cached = await self.get(f"cache:{cache_key}")
        if cached:
            return json.loads(cached)
        return None

    async def close(self):
        """Close the Redis connection."""
        if self.client:
            await self.client.close()


# Singleton instance
cache = RedisService()
