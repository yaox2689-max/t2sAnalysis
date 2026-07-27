"""DuckDB Executor — execute SQL queries against the analytics database.

Synchronous DuckDB calls are wrapped with asyncio timeout via
``asyncio.to_thread`` so long-running queries are cancelled.

Usage:
    from app.tools.duckdb_executor import DuckDBExecutor

    executor = DuckDBExecutor(duckdb_engine)
    result = await executor.execute("SELECT * FROM orders LIMIT 5")
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from typing import Any

import pandas as pd

from app.core.config import settings
from app.models.query import QueryResult
from app.tools.sql_safety import check_write_blocked

logger = logging.getLogger("t2s_analysis")


class DuckDBExecutionError(Exception):
    """Raised when SQL execution fails in DuckDB."""


class DuckDBWriteBlockedError(DuckDBExecutionError):
    """Raised when a write operation is attempted on the analytics database."""


class DuckDBExecutor:
    """Execute SQL queries against DuckDB and return QueryResult."""

    def __init__(
        self,
        duckdb_engine: Any,
        max_rows: int = settings.SQL_MAX_ROWS,
        timeout: int = settings.SQL_TIMEOUT,
    ) -> None:
        self._engine = duckdb_engine
        self.max_rows = max_rows
        self.timeout = timeout

    def _run_query(self, sql: str) -> pd.DataFrame:
        """Synchronous DuckDB query — runs in a thread."""
        result = self._engine.execute(sql)
        return result.fetchdf()

    def _preview_sync(self, table_name: str, limit: int = 5) -> pd.DataFrame:
        """Synchronous preview — runs in a thread."""
        safe = table_name.replace('"', '""')
        result = self._engine.execute(f'SELECT * FROM "{safe}" LIMIT {limit}')
        return result.fetchdf()

    async def preview_table(self, table_name: str, limit: int = 5) -> pd.DataFrame:
        """Return a preview DataFrame for the given table.

        Args:
            table_name: Name of the DuckDB table.
            limit: Maximum rows to return.
        """
        return await asyncio.to_thread(self._preview_sync, table_name, limit)

    async def execute(self, sql: str, **kwargs) -> QueryResult:
        """Execute SQL and return a QueryResult.

        Raises DuckDBWriteBlockedError on write operations.
        Raises DuckDBExecutionError on any database error or timeout.
        """
        warning = check_write_blocked(sql)
        if warning:
            raise DuckDBWriteBlockedError(f"Write operation blocked: {warning}")

        sql = re.sub(r'`([^`]+)`', r'"\1"', sql)

        start = time.perf_counter()

        try:
            df = await asyncio.wait_for(
                asyncio.to_thread(self._run_query, sql),
                timeout=self.timeout,
            )
        except asyncio.TimeoutError:
            raise DuckDBExecutionError(
                f"Query timed out after {self.timeout}s"
            )
        except Exception as exc:
            raise DuckDBExecutionError(str(exc)) from exc

        elapsed_ms = (time.perf_counter() - start) * 1000
        columns = list(df.columns)
        rows = df.to_dict("records")

        return QueryResult.from_rows(
            columns=columns,
            rows=rows,
            max_rows=self.max_rows,
            elapsed_ms=elapsed_ms,
        )
