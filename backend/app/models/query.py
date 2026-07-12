"""Shared data models for query results."""

from pydantic import BaseModel


class QueryResult(BaseModel):
    """Unified result format returned by SQL Executor.

    Used by Executor, Chart Tool, Insight Tool, and API responses.
    """

    columns: list[str]
    rows: list[dict]
    truncated: bool = False
    elapsed_ms: float = 0.0
    row_count: int = 0
