"""Executor Router — routes SQL to DuckDB or ExternalDB based on table source_type.

Parses SQL to find table names, checks the registry for their source,
and delegates to the correct executor. Results are cached via QueryCache.

Usage:
    router = ExecutorRouter(duckdb_executor, registry, external_executor, cache)
    result = await router.execute(sql, session_id="ses_abc", user_id="usr_123")
"""

from __future__ import annotations

import logging
from typing import Any, Optional

import sqlglot
import sqlglot.expressions as exp

from app.models.query import QueryResult

logger = logging.getLogger("t2s_analysis")


def _extract_table_names(sql: str) -> list[str]:
    """Extract table names from SQL using sqlglot AST."""
    try:
        tree = sqlglot.parse_one(sql)
    except sqlglot.errors.ParseError:
        return []

    tables = []
    for node in tree.walk():
        if isinstance(node, exp.Table):
            name = node.name
            if name:
                tables.append(name)
    return tables


class ExecutorRouter:
    """Routes SQL execution to DuckDB or ExternalDB based on table source_type."""

    def __init__(
        self,
        duckdb_executor: Any,
        registry: Any,
        external_executor: Any,
        connection_store: Any = None,
        cache: Any = None,
    ) -> None:
        self._duckdb = duckdb_executor
        self._external = external_executor
        self._registry = registry
        self._connections = connection_store
        self._cache = cache

    async def execute(
        self,
        sql: str,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> QueryResult:
        """Route to the correct executor based on table source_type.

        Checks cache first; on miss, executes and caches the result.
        """
        if self._cache:
            cached = await self._cache.get(sql, user_id=user_id)
            if cached is not None:
                return cached

        tables_in_query = _extract_table_names(sql)

        for table_name in tables_in_query:
            meta = self._registry.get_meta(table_name)
            if meta and meta.get("source_type") == "mysql":
                connection_id = meta.get("connection_id")
                if connection_id and self._connections:
                    cfg = await self._connections.get_config(connection_id)
                    if cfg:
                        result = await self._external.execute(sql, cfg)
                        if self._cache:
                            await self._cache.set(sql, result, user_id=user_id)
                        return result

        result = await self._duckdb.execute(sql)

        if self._cache:
            await self._cache.set(sql, result, user_id=user_id)

        return result
