"""
Redis-backed sliding window rate limiter middleware.

Uses a Redis sorted set per client IP to implement a true sliding window.
Falls back to in-memory if Redis is unavailable (development only).

For distributed deployments: Redis ensures limits are enforced consistently
across all API replicas.
"""

import time
from typing import Any

from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.core.logging import logger

# Paths exempt from rate limiting
_EXEMPT_PATHS = frozenset(
    {
        "/health",
        "/api/v1/health",
        "/api/v1/health/live",
        "/api/v1/health/ready",
    }
)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Redis-backed sliding window rate limiter.

    Falls back to in-memory if Redis is unavailable.
    """

    def __init__(self, app: Any, limit: int = 120, window_seconds: int = 60) -> None:
        super().__init__(app)
        self.limit = limit
        self.window_seconds = window_seconds
        # Fallback in-memory store (single-instance only)
        self._memory_cache: dict[str, list[float]] = {}

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path in _EXEMPT_PATHS:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        key = f"ratelimit:{client_ip}"
        now = time.time()
        window_start = now - self.window_seconds

        # Try Redis sliding window
        try:
            from app.services.redis import redis_service  # noqa: PLC0415

            if redis_service.client is not None:
                pipe = redis_service.client.pipeline()
                # Remove timestamps outside the window
                await pipe.zremrangebyscore(key, 0, window_start)  # type: ignore[attr-defined]
                # Count current requests in window
                await pipe.zcard(key)  # type: ignore[attr-defined]
                # Add current request timestamp
                await pipe.zadd(key, {str(now): now})  # type: ignore[attr-defined]
                # Set TTL so keys expire automatically
                await pipe.expire(key, self.window_seconds * 2)  # type: ignore[attr-defined]
                results = await pipe.execute()  # type: ignore[attr-defined]

                current_count: int = results[1]

                if current_count >= self.limit:
                    logger.warning("Rate limit exceeded (Redis)", ip=client_ip, count=current_count)
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail="Rate limit exceeded. Please try again later.",
                    )
                return await call_next(request)

        except HTTPException:
            raise
        except Exception as exc:
            logger.warning("Redis rate limiting unavailable, using in-memory fallback", error=str(exc))

        # In-memory fallback (single-process only)
        timestamps = self._memory_cache.get(client_ip, [])
        valid = [t for t in timestamps if now - t < self.window_seconds]

        if len(valid) >= self.limit:
            logger.warning("Rate limit exceeded (in-memory)", ip=client_ip, count=len(valid))
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later.",
            )

        valid.append(now)
        self._memory_cache[client_ip] = valid

        return await call_next(request)
