"""Safe SQL executor — timeout, row limit, elapsed measurement, and error wrapping.

This is the ONLY entry point for executing SQL in the Agent pipeline.
It wraps Database.execute() with safety guarantees:

- asyncio timeout (config.SQL_TIMEOUT)
- row limit via fetchmany (config.SQL_MAX_ROWS)
- truncation flag when result exceeds limit
- execution time measurement (elapsed_ms)
- custom exceptions instead of raw driver errors

Usage:
    from app.tools.sql_executor import SafeExecutor

    executor = SafeExecutor()
    result = await executor.execute("SELECT * FROM orders LIMIT 5")
"""

import asyncio
import time
from typing import Optional

from app.core.config import settings
from app.core.database import Database
from app.models.query import QueryResult


class ExecutionError(Exception):
    """Base exception for SQL execution failures."""


class ExecutionTimeoutError(ExecutionError):
    """Raised when SQL execution exceeds the configured timeout."""


class DatabaseError(ExecutionError):
    """Raised when the database returns an error."""


class SafeExecutor:
    """SQL executor with built-in safety controls."""

    def __init__(
        self,
        db: Optional[Database] = None,
        timeout: int = settings.SQL_TIMEOUT,
        max_rows: int = settings.SQL_MAX_ROWS,
    ) -> None:
        from app.core.database import db as _db

        self._db = db or _db
        self.timeout = timeout
        self.max_rows = max_rows

    async def execute(self, sql: str) -> QueryResult:
        """Execute SQL with timeout, row limit, and error handling."""
        start = time.perf_counter()

        try:
            rows = await asyncio.wait_for(
                self._db.execute(sql),
                timeout=self.timeout,
            )
        except asyncio.TimeoutError:
            elapsed_ms = (time.perf_counter() - start) * 1000
            raise ExecutionTimeoutError(
                f"SQL execution timed out after {self.timeout}s"
            ) from None
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start) * 1000
            raise DatabaseError(str(e)) from e

        elapsed_ms = (time.perf_counter() - start) * 1000

        if not rows:
            return QueryResult(
                columns=[],
                rows=[],
                row_count=0,
                elapsed_ms=round(elapsed_ms, 2),
            )

        columns = list(rows[0].keys())
        truncated = False

        if len(rows) > self.max_rows:
            rows = rows[: self.max_rows]
            truncated = True

        return QueryResult(
            columns=columns,
            rows=rows,
            truncated=truncated,
            row_count=len(rows),
            elapsed_ms=round(elapsed_ms, 2),
        )
