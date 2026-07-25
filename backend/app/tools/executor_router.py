"""Executor Router — routes SQL to DuckDB or ExternalDB based on table source_type.

Parses SQL to find table names, checks the registry for their source,
and delegates to the correct executor.

Usage:
    router = ExecutorRouter(duckdb_executor, registry, connection_store)
    result = await router.execute(sql, session_id="ses_abc", user_id="usr_123")
"""

import logging
from typing import Optional

import sqlglot
import sqlglot.expressions as exp

from app.models.query import QueryResult
from app.tools.sql_safety import check_write_blocked

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
        duckdb_executor: object,
        registry: object,
        external_executor: object,
        connection_store: object,
    ) -> None:
        self._duckdb = duckdb_executor
        self._external = external_executor
        self._registry = registry
        self._connections = connection_store

    async def execute(
        self,
        sql: str,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> QueryResult:
        """Route to the correct executor based on table source_type."""
        tables_in_query = _extract_table_names(sql)

        # Check if any table is a MySQL direct-connection table
        for table_name in tables_in_query:
            meta = self._registry._index.get(table_name)
            if meta and meta.get("source_type") == "mysql":
                connection_id = meta.get("connection_id")
                if connection_id and self._connections:
                    cfg = await self._connections.get_config(connection_id)
                    if cfg:
                        return await self._external.execute(sql, cfg)

        # Default: use DuckDB
        return await self._duckdb.execute(sql)
