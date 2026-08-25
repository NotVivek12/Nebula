from collections.abc import AsyncGenerator

import redis.asyncio as aioredis

from app.core.config import settings
from app.core.logging import logger


class RedisService:
    """Service class managing connection lifecycle and operations with Redis."""

    def __init__(self) -> None:
        self.redis: aioredis.Redis | None = None

    async def connect(self) -> None:
        """Establishes connection to the Redis service."""
        if not self.redis:
            self.redis = aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
            )
            logger.info("Connected to Redis")

    async def disconnect(self) -> None:
        """Closes the Redis connection pool."""
        if self.redis:
            await self.redis.close()
            self.redis = None
            logger.info("Disconnected from Redis")

    async def ping(self) -> bool:
        """Pings the Redis server to check connection health."""
        if not self.redis:
            return False
        try:
            return await self.redis.ping()
        except Exception as e:
            logger.error("Redis ping failed", error=str(e))
            return False

    async def get(self, key: str) -> str | None:
        """Retrieves a value from Redis cache."""
        if not self.redis:
            await self.connect()
        try:
            return await self.redis.get(key)  # type: ignore
        except Exception as e:
            logger.error("Redis GET operation failed", key=key, error=str(e))
            return None

    async def set(self, key: str, value: str, expire_seconds: int | None = None) -> bool:
        """Sets a value in Redis cache with an optional TTL."""
        if not self.redis:
            await self.connect()
        try:
            await self.redis.set(key, value, ex=expire_seconds)  # type: ignore
            return True
        except Exception as e:
            logger.error("Redis SET operation failed", key=key, error=str(e))
            return False

    async def delete(self, key: str) -> bool:
        """Removes a key from Redis cache."""
        if not self.redis:
            await self.connect()
        try:
            await self.redis.delete(key)  # type: ignore
            return True
        except Exception as e:
            logger.error("Redis DELETE operation failed", key=key, error=str(e))
            return False


# Singleton instance
redis_service = RedisService()


async def get_redis_client() -> AsyncGenerator[aioredis.Redis, None]:
    """Dependency injector for raw Redis client access."""
    if not redis_service.redis:
        await redis_service.connect()
    assert redis_service.redis is not None
    yield redis_service.redis
