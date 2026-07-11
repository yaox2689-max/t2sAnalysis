"""Asynchronous Redis client with connection pool support.

This module provides the foundational RedisClient class used for
session storage, caching, and other data-access needs.

It is a thin wrapper around redis.asyncio — no business logic,
no schema cache, no conversation serialisation.

Usage:
    from app.core.redis import redis_client

    await redis_client.set("key", "value")
    value = await redis_client.get("key")
"""

from typing import Optional

from redis.asyncio import ConnectionPool, Redis
from redis.asyncio.retry import Retry
from redis.backoff import ExponentialBackoff
from redis.exceptions import ConnectionError, TimeoutError

from app.core.config import settings


class RedisClient:
    """Async Redis wrapper — connection pool, basic get/set/delete/exists."""

    def __init__(self) -> None:
        self._pool: Optional[ConnectionPool] = None
        self._client: Optional[Redis] = None

    def init(self) -> None:
        """Initialise the connection pool."""
        if self._client is not None:
            return

        retry = Retry(ExponentialBackoff(), retries=3)

        self._pool = ConnectionPool(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            max_connections=settings.REDIS_MAX_CONNECTIONS,
            retry_on_error=[ConnectionError, TimeoutError],
        )

        self._client = Redis(
            connection_pool=self._pool,
            retry=retry,
            retry_on_error=[ConnectionError, TimeoutError],
        )

    async def close(self) -> None:
        """Close the connection pool."""
        if self._client is None:
            return
        await self._client.aclose()
        self._client = None
        self._pool = None

    async def get(self, key: str) -> Optional[str]:
        """Get a value by key. Returns None if not found."""
        if self._client is None:
            raise RuntimeError("Redis not initialised — call redis_client.init() first")
        value = await self._client.get(key)
        return value.decode("utf-8") if value is not None else None

    async def set(self, key: str, value: str, expire: Optional[int] = None) -> None:
        """Set a key-value pair with optional TTL (seconds)."""
        if self._client is None:
            raise RuntimeError("Redis not initialised — call redis_client.init() first")
        await self._client.set(key, value, ex=expire)

    async def delete(self, key: str) -> bool:
        """Delete a key. Returns True if the key existed."""
        if self._client is None:
            raise RuntimeError("Redis not initialised — call redis_client.init() first")
        return await self._client.delete(key) > 0

    async def exists(self, key: str) -> bool:
        """Check if a key exists."""
        if self._client is None:
            raise RuntimeError("Redis not initialised — call redis_client.init() first")
        return await self._client.exists(key) > 0


# Module-level singleton
redis_client = RedisClient()
