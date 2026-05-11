from typing import Dict, Any, Optional
import time
import hashlib
import json
import os


class CacheEntry:
    def __init__(self, value: Any, ttl: int = 300):
        self.value = value
        self.expires_at = time.time() + ttl

    def is_expired(self) -> bool:
        return time.time() > self.expires_at


class RedisCache:
    """Optional Redis cache adapter."""
    
    def __init__(self):
        self.redis = None
        self._connect()
    
    def _connect(self):
        try:
            import redis
            redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
            self.redis = redis.from_url(redis_url, decode_responses=True)
            self.redis.ping()
        except Exception:
            self.redis = None
    
    def get(self, key: str) -> Optional[Any]:
        if not self.redis:
            return None
        try:
            value = self.redis.get(key)
            return json.loads(value) if value else None
        except Exception:
            return None
    
    def set(self, key: str, value: Any, ttl: int = 300):
        if not self.redis:
            return
        try:
            self.redis.setex(key, ttl, json.dumps(value, default=str))
        except Exception:
            pass
    
    def invalidate(self, key: str):
        if self.redis:
            self.redis.delete(key)
    
    def clear(self):
        if self.redis:
            self.redis.flushdb()


class InMemoryCache:
    """Fallback in-memory cache."""

    def __init__(self):
        self._cache: Dict[str, CacheEntry] = {}
    
    def get(self, key: str) -> Optional[Any]:
        entry = self._cache.get(key)
        if entry and not entry.is_expired():
            return entry.value
        if entry:
            del self._cache[key]
        return None

    def set(self, key: str, value: Any, ttl: int = 300):
        self._cache[key] = CacheEntry(value, ttl)

    def invalidate(self, key: str):
        if key in self._cache:
            del self._cache[key]

    def clear(self):
        self._cache.clear()


class RequestCache:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._cache = None
            cls._instance._use_redis = False
            cls._instance._init_cache()
        return cls._instance

    def _init_cache(self):
        try:
            self._cache = RedisCache()
            self._cache.redis.ping()
            self._use_redis = True
            return
        except Exception:
            pass
        self._cache = InMemoryCache()
        self._use_redis = False

    @staticmethod
    def generate_key(prefix: str, data: Any) -> str:
        data_str = json.dumps(data, sort_keys=True, default=str)
        hash_value = hashlib.md5(data_str.encode()).hexdigest()
        return f"{prefix}:{hash_value}"

    def get(self, key: str) -> Optional[Any]:
        return self._cache.get(key)

    def set(self, key: str, value: Any, ttl: int = 300):
        self._cache.set(key, value, ttl)

    def invalidate(self, key: str):
        self._cache.invalidate(key)

    def clear(self):
        self._cache.clear()

    def cleanup(self):
        if not self._use_redis and hasattr(self._cache, '_cache'):
            expired_keys = [k for k, v in self._cache._cache.items() if v.is_expired()]
            for key in expired_keys:
                del self._cache._cache[key]

    def stats(self) -> Dict[str, Any]:
        if self._use_redis:
            return {"backend": "redis", "status": "connected"}
        entry_count = len(self._cache._cache) if hasattr(self._cache, '_cache') else 0
        return {"backend": "memory", "entries": entry_count, "status": "active"}


cache = RequestCache()
