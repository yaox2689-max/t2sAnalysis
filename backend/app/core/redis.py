"""Redis client — async Redis wrapper for caching.

Lazy-initializes on first use. Falls back gracefully if Redis is unavailable.

Usage:
    from app.core.redis import redis_client
    await redis_client.set("key", "value", expire=3600)
    val = await redis_client.get("key")
"""

import logging
from typing import Optional

logger = logging.getLogger("t2s_analysis")


class RedisClient:
    """Async Redis wrapper with lazy initialization."""

    def __init__(self) -> None:
        self._client = None

    def init(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        max_connections: int = 10,
    ) -> None:
        """Initialize Redis connection pool."""
        try:
            import redis.asyncio as aioredis
            self._client = aioredis.Redis(
                host=host, port=port, db=db,
                max_connections=max_connections,
                decode_responses=True,
                socket_connect_timeout=3,
            )
            logger.info({"event": "redis_init", "host": host, "port": port})
        except Exception as exc:
            logger.warning({"event": "redis_init_failed", "error": str(exc)[:100]})
            self._client = None

    @property
    def is_available(self) -> bool:
        return self._client is not None

    async def get(self, key: str) -> Optional[str]:
        if not self._client:
            return None
        try:
            return await self._client.get(key)
        except Exception:
            return None

    async def set(self, key: str, value: str, expire: int = 3600) -> bool:
        if not self._client:
            return False
        try:
            await self._client.set(key, value, ex=expire)
            return True
        except Exception:
            return False

    async def delete(self, key: str) -> bool:
        if not self._client:
            return False
        try:
            return bool(await self._client.delete(key))
        except Exception:
            return False

    async def close(self) -> None:
        if self._client:
            await self._client.close()
            self._client = None


# Module-level singleton
redis_client = RedisClient()
