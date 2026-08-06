"""API 响应缓存 — 线程安全 LRU 内存缓存"""
import time
import threading
import functools
import hashlib
from collections import OrderedDict
from typing import Any, Callable, Optional


class LRUCache:
    def __init__(self, maxsize: int = 128, ttl: int = 30):
        self._cache: OrderedDict[str, tuple[float, Any]] = OrderedDict()
        self._maxsize = maxsize
        self._ttl = ttl
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None
            expires, value = self._cache[key]
            if time.monotonic() > expires:
                del self._cache[key]
                self._misses += 1
                return None
            self._cache.move_to_end(key)
            self._hits += 1
            return value

    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            self._cache[key] = (time.monotonic() + (ttl or self._ttl), value)
            while len(self._cache) > self._maxsize:
                self._cache.popitem(last=False)

    def clear(self):
        with self._lock:
            self._cache.clear()

    @property
    def stats(self) -> dict:
        with self._lock:
            total = self._hits + self._misses
            return {
                "size": len(self._cache),
                "maxsize": self._maxsize,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": round(self._hits / max(total, 1), 3),
            }


_cache = LRUCache(maxsize=256, ttl=60)


def cached(ttl: int = 30, key_prefix: str = ""):
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            cache_key = key_prefix + hashlib.md5(
                (func.__name__ + str(args) + str(sorted(kwargs.items()))).encode()
            ).hexdigest()[:16]
            result = _cache.get(cache_key)
            if result is not None:
                return result
            result = await func(*args, **kwargs)
            _cache.set(cache_key, result, ttl)
            return result
        return wrapper
    return decorator


def get_cache() -> LRUCache:
    return _cache
