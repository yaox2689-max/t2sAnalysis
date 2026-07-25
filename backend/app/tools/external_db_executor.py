"""External DB Executor — execute read-only SQL against external MySQL databases.

Each connection gets its own SQLAlchemy async engine with connection pooling.
Write operations are blocked via sqlglot (same as DuckDBExecutor).

Usage:
    executor = ExternalDBExecutor()
    result = await executor.execute("SELECT * FROM orders", connection_config)
"""

import asyncio
import logging
import time
from typing import Optional

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.models.query import QueryResult
from app.tools.sql_safety import check_write_blocked

logger = logging.getLogger("t2s_analysis")

MAX_ROWS = 500


class ExternalDBError(Exception):
    """Raised when SQL execution fails on an external database."""


class ExternalDBWriteBlockedError(ExternalDBError):
    """Raised when a write operation is attempted."""


class ExternalDBExecutor:
    """Execute read-only SQL against external MySQL databases."""

    def __init__(self, max_rows: int = MAX_ROWS, timeout: int = 10) -> None:
        self._engines: dict[str, AsyncEngine] = {}
        self.max_rows = max_rows
        self.timeout = timeout

    def _engine_key(self, cfg: dict) -> str:
        return f"{cfg['host']}:{cfg['port']}/{cfg['database']}"

    def _get_engine(self, cfg: dict) -> AsyncEngine:
        """Get or create a SQLAlchemy async engine for this connection."""
        key = self._engine_key(cfg)
        if key not in self._engines:
            url = (
                f"mysql+aiomysql://{cfg['username']}:{cfg['password']}"
                f"@{cfg['host']}:{cfg['port']}"
                f"/{cfg['database']}?charset=utf8mb4"
            )
            self._engines[key] = create_async_engine(
                url, pool_size=3, pool_pre_ping=True, pool_recycle=3600,
            )
        return self._engines[key]

    async def test_connection(self, cfg: dict) -> list[str]:
        """Test a connection and return list of table names."""
        engine = self._get_engine(cfg)
        async with engine.connect() as conn:
            result = await conn.execute(
                __import__("sqlalchemy").text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = :db AND table_type = 'BASE TABLE'"
                ),
                {"db": cfg["database"]},
            )
            rows = result.fetchall()
            return [r[0] for r in rows]

    async def introspect_tables(self, cfg: dict) -> dict[str, list[dict]]:
        """Get column metadata for all tables in the database."""
        engine = self._get_engine(cfg)
        async with engine.connect() as conn:
            result = await conn.execute(
                __import__("sqlalchemy").text(
                    "SELECT table_name, column_name, data_type "
                    "FROM information_schema.columns "
                    "WHERE table_schema = :db ORDER BY table_name, ordinal_position"
                ),
                {"db": cfg["database"]},
            )
            rows = result.fetchall()

        tables: dict[str, list[dict]] = {}
        for table_name, col_name, data_type in rows:
            tables.setdefault(table_name, []).append(
                {"name": col_name, "data_type": data_type, "original_name": col_name}
            )
        return tables

    def invalidate(self, cfg: dict) -> None:
        """Dispose engine for a deleted connection."""
        key = self._engine_key(cfg)
        engine = self._engines.pop(key, None)
        if engine:
            import asyncio
            asyncio.get_event_loop().create_task(engine.dispose())

    async def execute(self, sql: str, connection_config: dict) -> QueryResult:
        """Execute read-only SQL and return QueryResult."""
        warning = check_write_blocked(sql)
        if warning:
            raise ExternalDBWriteBlockedError(f"Write operation blocked: {warning}")

        engine = self._get_engine(connection_config)
        start = time.perf_counter()

        try:
            async with engine.connect() as conn:
                result = await asyncio.wait_for(
                    conn.execute(__import__("sqlalchemy").text(sql)),
                    timeout=self.timeout,
                )
                rows_raw = result.fetchall()
                columns = list(result.keys())
        except asyncio.TimeoutError:
            raise ExternalDBError(f"Query timed out after {self.timeout}s")
        except Exception as exc:
            raise ExternalDBError(str(exc)) from exc

        elapsed_ms = (time.perf_counter() - start) * 1000

        rows = [dict(zip(columns, row)) for row in rows_raw]

        # Clean NaN/Inf
        rows = [
            {k: (None if isinstance(v, float) and (v != v or v == float("inf") or v == float("-inf")) else v)
             for k, v in row.items()}
            for row in rows
        ]

        truncated = False
        if len(rows) > self.max_rows:
            rows = rows[:self.max_rows]
            truncated = True

        return QueryResult(
            columns=columns,
            rows=rows,
            truncated=truncated,
            row_count=len(rows),
            elapsed_ms=round(elapsed_ms, 2),
        )
