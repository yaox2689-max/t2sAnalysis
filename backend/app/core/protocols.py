"""Protocol definitions for dependency injection.

These Protocol classes define the interfaces expected by consumers,
replacing ``object`` type annotations and enabling static type checking
without circular imports.

Usage::

    from app.core.protocols import DuckDBEngineProtocol

    def __init__(self, engine: DuckDBEngineProtocol) -> None:
        ...
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from app.models.query import QueryResult


@runtime_checkable
class DuckDBEngineProtocol(Protocol):
    """Interface for the DuckDB engine wrapper."""

    def execute(self, sql: str) -> Any:
        """Execute SQL and return a DuckDB result."""
        ...

    def tables(self) -> list[str]:
        """Return all table names in the database."""
        ...

    @property
    def conn(self) -> Any:
        """Return the underlying DuckDB connection."""
        ...


@runtime_checkable
class DuckDBExecutorProtocol(Protocol):
    """Interface for the async DuckDB executor."""

    async def execute(self, sql: str) -> QueryResult:
        """Execute SQL asynchronously and return a QueryResult."""
        ...

    async def preview_table(self, table_name: str, limit: int = 5) -> Any:
        """Return a preview DataFrame for the given table."""
        ...


@runtime_checkable
class SchemaProfilerProtocol(Protocol):
    """Interface for the schema profiler."""

    async def profile(self, table_name: str) -> dict:
        """Profile a table and return column metadata."""
        ...


@runtime_checkable
class DatasetRegistryProtocol(Protocol):
    """Interface for the dataset registry (data catalog)."""

    def register(
        self,
        table_name: str,
        display_name: str,
        source_type: str,
        session_id: str | None = None,
        user_id: str | None = None,
        columns_meta: list[dict] | None = None,
    ) -> None:
        """Register a dataset in the catalog."""
        ...

    def unregister(self, table_name: str) -> None:
        """Remove a dataset from the catalog."""
        ...

    async def get_catalog(
        self,
        session_id: str | None = None,
        user_id: str | None = None,
        top_k: int = 10,
        question: str | None = None,
    ) -> Any:
        """Get the catalog of visible datasets."""
        ...

    async def get_table_schema(self, table_name: str) -> Any:
        """Get the full schema for a single table."""
        ...

    def list_tables(self, source_type: str | None = None) -> list[str]:
        """List all registered table names."""
        ...

    def get_meta(self, table_name: str) -> dict | None:
        """Get raw metadata for a table."""
        ...

    def set_meta(self, table_name: str, key: str, value: Any) -> None:
        """Set a metadata field on a registered table."""
        ...

    def count_external_tables(self, connection_id: str) -> int:
        """Count tables associated with a connection."""
        ...

    def iter_by_connection(self, connection_id: str) -> Any:
        """Iterate table names for a given connection."""
        ...


@runtime_checkable
class QueryCacheProtocol(Protocol):
    """Interface for the query result cache."""

    async def get(self, sql: str, user_id: str | None = None) -> QueryResult | None:
        """Look up cached result."""
        ...

    async def set(self, sql: str, result: QueryResult, user_id: str | None = None) -> None:
        """Store a result in cache."""
        ...


@runtime_checkable
class ExternalDBExecutorProtocol(Protocol):
    """Interface for the external MySQL executor."""

    async def execute(self, sql: str, config: dict) -> QueryResult:
        """Execute SQL against an external MySQL database."""
        ...
