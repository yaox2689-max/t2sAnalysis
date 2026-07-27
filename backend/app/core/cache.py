"""Query Cache — SQL execution result cache backed by Redis.

Caches QueryResult keyed by user_id + SQL hash. Each user has
independent cache. TTL defaults to 1 hour.

Redis key format: cache:sql:{user_id}:{sha256_prefix}

Usage:
    cache = QueryCache(redis_client)
    cached = await cache.get(sql, user_id="usr_123")
    if cached is None:
        result = await executor.execute(sql)
        await cache.set(sql, result, user_id="usr_123")
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Optional

from app.core.config import settings
from app.core.utils import truncate_error
from app.models.query import QueryResult

logger = logging.getLogger("t2s_analysis")

KEY_PREFIX = "cache:sql"


class QueryCache:
    """SQL execution result cache backed by Redis."""

    def __init__(self, redis_client: object, ttl_seconds: int | None = None) -> None:
        self._redis = redis_client
        self.ttl = ttl_seconds if ttl_seconds is not None else settings.CACHE_TTL_SECONDS

    @staticmethod
    def _make_key(sql: str, user_id: Optional[str] = None) -> str:
        """Generate Redis key: cache:sql:{user_id}:{hash}."""
        normalized = " ".join(sql.split()).strip().lower()
        sql_hash = hashlib.sha256(normalized.encode()).hexdigest()[:16]
        uid = user_id or "global"
        return f"{KEY_PREFIX}:{uid}:{sql_hash}"

    async def get(self, sql: str, user_id: Optional[str] = None) -> Optional[QueryResult]:
        """Look up cached result. Returns None on miss."""
        key = self._make_key(sql, user_id)
        try:
            data = await self._redis.get(key)
            if data:
                if isinstance(data, bytes):
                    data = data.decode()
                parsed = json.loads(data)
                result = QueryResult(**parsed)
                logger.info({"event": "cache_hit", "key": key, "row_count": result.row_count})
                return result
        except Exception as exc:
            logger.warning({"event": "cache_get_error", "error": truncate_error(exc, 100)})
        return None

    async def set(self, sql: str, result: QueryResult, user_id: Optional[str] = None) -> None:
        """Store a query result in cache with TTL."""
        key = self._make_key(sql, user_id)
        try:
            await self._redis.set(key, result.model_dump_json(), expire=self.ttl)
            logger.info({"event": "cache_set", "key": key, "ttl": self.ttl})
        except Exception as exc:
            logger.warning({"event": "cache_set_error", "error": truncate_error(exc, 100)})
