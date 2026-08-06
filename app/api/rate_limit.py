"""API 限流中间件 — 基于滑动窗口算法的内存限流器"""
import time
import threading
from collections import defaultdict
from fastapi import Request
from fastapi.responses import JSONResponse

DEFAULT_RATE_LIMIT = 60
DEFAULT_WINDOW_SEC = 60


class RateLimiter:
    def __init__(self, max_requests: int = DEFAULT_RATE_LIMIT,
                 window_seconds: int = DEFAULT_WINDOW_SEC):
        self._max = max_requests
        self._window = window_seconds
        self._buckets: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def _clean(self, key: str, now: float) -> list[float]:
        cutoff = now - self._window
        self._buckets[key] = [t for t in self._buckets[key] if t > cutoff]
        return self._buckets[key]

    def is_allowed(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            timestamps = self._clean(key, now)
            if len(timestamps) < self._max:
                timestamps.append(now)
                return True
            return False


_limiter = RateLimiter()
_SKIP_PREFIXES = ("/api/dashboard", "/health", "/favicon.ico", "/assets/", "/docs", "/redoc", "/openapi.json")


async def rate_limit_middleware(request: Request, call_next):
    path = request.url.path
    if any(path == p or path.startswith(p) for p in _SKIP_PREFIXES):
        return await call_next(request)

    client_ip = request.client.host if request.client else "unknown"
    if not _limiter.is_allowed(client_ip):
        return JSONResponse(status_code=429, content={
            "code": 429, "data": None, "message": "请求过于频繁，请稍后重试"
        })

    return await call_next(request)


def get_rate_limiter() -> RateLimiter:
    return _limiter
