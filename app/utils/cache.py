"""简单 TTL 缓存装饰器"""
import time
from functools import wraps
from typing import Any, Callable


def ttl_cache(ttl_seconds: float = 30):
    """带过期时间的缓存"""

    def decorator(func: Callable) -> Callable:
        cache: dict[str, tuple[float, Any]] = {}

        @wraps(func)
        async def wrapper(*args, **kwargs):
            key = str(args) + str(sorted(kwargs.items()))
            now = time.time()
            if key in cache:
                ts, val = cache[key]
                if now - ts < ttl_seconds:
                    return val
            result = await func(*args, **kwargs)
            cache[key] = (now, result)
            return result

        return wrapper

    return decorator
