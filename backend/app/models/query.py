"""Shared data models for query results."""

from __future__ import annotations

from pydantic import BaseModel

from app.core.utils import sanitize_float


class QueryResult(BaseModel):
    """Unified result format returned by SQL Executor.

    Used by Executor, Chart Tool, Insight Tool, and API responses.
    """

    columns: list[str]
    rows: list[dict]
    truncated: bool = False
    elapsed_ms: float = 0.0
    row_count: int = 0

    @classmethod
    def from_rows(
        cls,
        columns: list[str],
        rows: list[dict],
        max_rows: int,
        elapsed_ms: float = 0.0,
    ) -> QueryResult:
        """Build a QueryResult from raw rows with NaN sanitisation and truncation.

        Args:
            columns: Column names.
            rows: Raw row dicts.
            max_rows: Maximum rows to return.  Excess rows are truncated.
            elapsed_ms: Query execution time in milliseconds.
        """
        rows = [{k: sanitize_float(v) for k, v in row.items()} for row in rows]
        truncated = len(rows) > max_rows
        if truncated:
            rows = rows[:max_rows]
        return cls(
            columns=columns,
            rows=rows,
            truncated=truncated,
            row_count=len(rows),
            elapsed_ms=round(elapsed_ms, 2),
        )
