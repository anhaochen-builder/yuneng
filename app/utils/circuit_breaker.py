"""熔断器 — 防止级联故障"""
import time
import threading
import functools
from enum import Enum
from typing import Callable


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    def __init__(self, name: str, failure_threshold: int = 5,
                 recovery_timeout: int = 30, half_open_limit: int = 2):
        self.name = name
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._half_open_limit = half_open_limit
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._half_open_successes = 0
        self._last_failure_time = 0.0
        self._lock = threading.Lock()

    @property
    def state(self) -> str:
        return self._state.value

    def call(self, func: Callable, *args, **kwargs):
        with self._lock:
            if self._state == CircuitState.OPEN:
                if time.monotonic() - self._last_failure_time > self._recovery_timeout:
                    self._state = CircuitState.HALF_OPEN
                    self._half_open_successes = 0
                else:
                    raise CircuitOpenError(f"熔断器 [{self.name}] 已断开")

        try:
            result = func(*args, **kwargs)
            with self._lock:
                if self._state == CircuitState.HALF_OPEN:
                    self._half_open_successes += 1
                    if self._half_open_successes >= self._half_open_limit:
                        self._state = CircuitState.CLOSED
                        self._failure_count = 0
                else:
                    self._failure_count = 0
            return result
        except Exception as e:
            with self._lock:
                self._failure_count += 1
                self._last_failure_time = time.monotonic()
                if self._failure_count >= self._failure_threshold:
                    self._state = CircuitState.OPEN
            raise e


class CircuitOpenError(Exception):
    pass


_breakers: dict[str, CircuitBreaker] = {}
_breaker_lock = threading.Lock()


def get_breaker(name: str, **kwargs) -> CircuitBreaker:
    with _breaker_lock:
        if name not in _breakers:
            _breakers[name] = CircuitBreaker(name, **kwargs)
        return _breakers[name]


def circuit_breaker(name: str, **kwargs):
    """装饰器: 为函数添加熔断保护"""
    def decorator(func: Callable):
        breaker = get_breaker(name, **kwargs)
        @functools.wraps(func)
        def wrapper(*args, **kw):
            return breaker.call(func, *args, **kw)
        return wrapper
    return decorator
