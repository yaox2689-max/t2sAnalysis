"""Asynchronous database engine and session management.

This module provides the foundational Database class used by all
Repository layers. It owns the SQLAlchemy AsyncEngine lifecycle
and exposes an execute() method for running SQL statements.

Usage:
    from app.core.database import db

    result = await db.execute("SELECT 1")
"""

from typing import Any, Optional, Union

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, create_async_engine

from app.core.config import settings


class Database:
    """Async SQLAlchemy wrapper — engine init, session, health."""

    def __init__(self) -> None:
        self._engine: AsyncEngine | None = None

    @property
    def is_initialized(self) -> bool:
        """Whether the engine has been initialised."""
        return self._engine is not None

    @property
    def url(self) -> str:
        return (
            f"mysql+aiomysql://{settings.DB_USER}:{settings.DB_PASSWORD}"
            f"@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
            f"?charset=utf8mb4"
        )

    def init(self) -> None:
        """Initialise the async engine with connection pool settings."""
        if self._engine is not None:
            return
        self._engine = create_async_engine(
            self.url,
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
            pool_timeout=settings.DB_POOL_TIMEOUT,
            pool_recycle=settings.DB_POOL_RECYCLE,
            pool_pre_ping=True,
            echo=settings.DEBUG,
        )

    async def close(self) -> None:
        """Dispose the engine and release all connections."""
        if self._engine is None:
            return
        await self._engine.dispose()
        self._engine = None

    async def execute(self, sql: str, params: Optional[Union[dict, tuple]] = None) -> list[dict]:
        """Execute a raw SQL query and return rows as dicts.

        Supports both dict-style (:key) and positional (? / %s) params.
        For INSERT/UPDATE/DELETE returning nothing, returns an empty list.
        """
        if self._engine is None:
            raise RuntimeError("Database not initialised — call db.init() first")

        async with self._engine.connect() as conn:
            conn: AsyncConnection
            result = await conn.execute(text(sql), params)
            if result.returns_rows:
                rows = result.fetchall()
                columns = list(result.keys())
                return [dict(zip(columns, row)) for row in rows]
            await conn.commit()
            return []

    async def execute_insert(self, sql: str, params: Optional[Union[dict, tuple]] = None) -> int:
        """Execute an INSERT statement and return the lastrowid.

        Returns 0 if no row was inserted.
        """
        if self._engine is None:
            raise RuntimeError("Database not initialised — call db.init() first")

        async with self._engine.connect() as conn:
            conn: AsyncConnection
            result = await conn.execute(text(sql), params)
            await conn.commit()
            return result.lastrowid if result.lastrowid else 0

    async def health(self) -> bool:
        """Quick connectivity check — returns True if the database responds."""
        try:
            await self.execute("SELECT 1")
            return True
        except Exception:
            return False


# Module-level singleton
db = Database()
