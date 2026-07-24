"""DuckDB Executor — execute SQL queries against the analytics database.

Replaces SafeExecutor (MySQL) for all analysis queries.
DuckDB is synchronous and fast, so no timeout wrapping needed.

Usage:
    from app.tools.duckdb_executor import DuckDBExecutor

    executor = DuckDBExecutor(duckdb_engine)
    result = await executor.execute("SELECT * FROM orders LIMIT 5")
"""

import logging
import time
from typing import Optional

from app.models.query import QueryResult

logger = logging.getLogger("t2s_analysis")

# Safety limits
MAX_ROWS = 500


class DuckDBExecutionError(Exception):
    """Raised when SQL execution fails in DuckDB."""


class DuckDBExecutor:
    """Execute SQL queries against DuckDB and return QueryResult."""

    def __init__(self, duckdb_engine: object, max_rows: int = MAX_ROWS) -> None:
        self._engine = duckdb_engine
        self.max_rows = max_rows

    async def execute(self, sql: str) -> QueryResult:
        """Execute SQL and return a QueryResult.

        Raises DuckDBExecutionError on any database error.
        """
        start = time.perf_counter()

        try:
            result = self._engine.execute(sql)
            df = result.fetchdf()
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - start) * 1000
            raise DuckDBExecutionError(str(exc)) from exc

        elapsed_ms = (time.perf_counter() - start) * 1000

        columns = list(df.columns)
        rows = df.to_dict("records")
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
