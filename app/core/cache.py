import functools
from typing import Any, Callable


class RedisCacheManager:
    """Redis cache connector managing in-memory cache fallbacks."""

    def __init__(self) -> None:
        self._local_store: dict[str, Any] = {}

    def get(self, key: str) -> Any:
        return self._local_store.get(key)

    def set(self, key: str, value: Any, expire_seconds: int = 60) -> None:
        self._local_store[key] = value


cache_manager = RedisCacheManager()


def cache_response(expire_seconds: int = 60) -> Callable:
    """Decorator cache wrapper to cache endpoint JSON results."""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            cached = cache_manager.get(cache_key)
            if cached is not None:
                return cached

            res = await func(*args, **kwargs)
            cache_manager.set(cache_key, res, expire_seconds)
            return res

        return wrapper

    return decorator
