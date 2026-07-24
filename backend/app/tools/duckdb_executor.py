"""DuckDB Executor — execute SQL queries against the analytics database.

Replaces SafeExecutor (MySQL) for all analysis queries.
DuckDB is synchronous and fast, so no timeout wrapping needed.

Usage:
    from app.tools.duckdb_executor import DuckDBExecutor

    executor = DuckDBExecutor(duckdb_engine)
    result = await executor.execute("SELECT * FROM orders LIMIT 5")
"""

import logging
import re
import time
from typing import Optional

import sqlglot
import sqlglot.expressions as exp

from app.models.query import QueryResult

logger = logging.getLogger("t2s_analysis")

# Safety limits
MAX_ROWS = 500

# Blocked write operations
_WRITE_OPS = frozenset({
    exp.Insert, exp.Update, exp.Delete,
    exp.Drop, exp.Alter, exp.Create, exp.Grant,
})


class DuckDBExecutionError(Exception):
    """Raised when SQL execution fails in DuckDB."""


class DuckDBWriteBlockedError(DuckDBExecutionError):
    """Raised when a write operation is attempted on the analytics database."""


def _check_write_blocked(sql: str) -> Optional[str]:
    """Check if SQL contains write operations. Returns warning or None."""
    try:
        tree = sqlglot.parse_one(sql)
    except sqlglot.errors.ParseError:
        return None  # let execution handle the parse error

    for node in tree.walk():
        if isinstance(node, tuple(_WRITE_OPS)):
            return f"WRITE_OPERATION: {node.key.upper()}"
    return None


class DuckDBExecutor:
    """Execute SQL queries against DuckDB and return QueryResult."""

    def __init__(self, duckdb_engine: object, max_rows: int = MAX_ROWS) -> None:
        self._engine = duckdb_engine
        self.max_rows = max_rows

    async def execute(self, sql: str) -> QueryResult:
        """Execute SQL and return a QueryResult.

        Raises DuckDBWriteBlockedError on write operations.
        Raises DuckDBExecutionError on any database error.
        """
        # Safety check: block write operations
        warning = _check_write_blocked(sql)
        if warning:
            raise DuckDBWriteBlockedError(f"Write operation blocked: {warning}")

        # Normalize: convert backtick-quoted identifiers to double-quote
        # DuckDB handles double-quoted Unicode identifiers more reliably
        sql = re.sub(r'`([^`]+)`', r'"\1"', sql)

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

        # Clean NaN / Inf values → None (JSON-safe)
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
