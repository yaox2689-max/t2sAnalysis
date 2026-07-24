"""DatasetRegistry — the AI's data catalog (Catalog).

Manages all datasets visible to the AI. Replaces SchemaRetriever.
SQL Generator only reads from here.

Usage:
    from app.services.dataset_registry import DatasetRegistry

    registry = DatasetRegistry(duckdb_engine, profiler)
    catalog = registry.get_catalog(session_id="ses_abc")
    schema = registry.get_table_schema("orders")
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("t2s_analysis")


@dataclass
class ColumnSchema:
    """A column's full description (schema + profile)."""
    name: str
    data_type: str
    semantic_type: str
    null_ratio: float = 0.0
    unique_count: int = 0
    min_value: Optional[str] = None
    max_value: Optional[str] = None
    top_values: list[str] = field(default_factory=list)
    original_name: Optional[str] = None


@dataclass
class TableSchema:
    """A table's full description (schema + profile)."""
    table_name: str
    display_name: str
    source_type: str            # "demo" | "excel" | "csv"
    session_id: Optional[str] = None
    row_count: int = 0
    columns: list[ColumnSchema] = field(default_factory=list)


@dataclass
class Catalog:
    """The AI's data directory — all visible datasets."""
    tables: list[TableSchema] = field(default_factory=list)


class DatasetRegistry:
    """Manage the catalog of all datasets visible to the AI."""

    def __init__(self, duckdb_engine: object, profiler: object = None) -> None:
        self._engine = duckdb_engine
        self._profiler = profiler
        # In-memory index: table_name → metadata
        self._index: dict[str, dict] = {}

    def register(
        self,
        table_name: str,
        display_name: str,
        source_type: str,
        session_id: Optional[str] = None,
        columns_meta: Optional[list[dict]] = None,
    ) -> None:
        """Register a dataset in the catalog."""
        self._index[table_name] = {
            "display_name": display_name,
            "source_type": source_type,
            "session_id": session_id,
            "columns_meta": columns_meta or [],
        }
        logger.info({"event": "dataset_registered", "table": table_name, "source": source_type})

    def unregister(self, table_name: str) -> None:
        """Remove a dataset from the catalog."""
        self._index.pop(table_name, None)
        logger.info({"event": "dataset_unregistered", "table": table_name})

    def get_catalog(
        self,
        session_id: Optional[str] = None,
        top_k: int = 10,
        question: Optional[str] = None,
    ) -> Catalog:
        """Get the catalog — all datasets visible to the current session.

        Args:
            session_id: Filter by session (demo data always included).
            top_k: Maximum tables to return (controls prompt size).
            question: Optional question for future relevance-based sorting.

        Returns:
            Demo datasets + session's own uploaded datasets.
        """
        tables = []
        for table_name, meta in self._index.items():
            # Filter: show demo data + current session's data
            if meta["source_type"] == "demo" or meta["session_id"] == session_id:
                schema = self._build_table_schema(table_name, meta)
                if schema:
                    tables.append(schema)

        # Limit to top_k
        if len(tables) > top_k:
            tables = tables[:top_k]

        return Catalog(tables=tables)

    def get_table_schema(self, table_name: str) -> Optional[TableSchema]:
        """Get the full schema for a single table."""
        meta = self._index.get(table_name)
        if not meta:
            return None
        return self._build_table_schema(table_name, meta)

    def list_tables(self, source_type: Optional[str] = None) -> list[str]:
        """List all registered table names, optionally filtered by source."""
        if source_type:
            return [t for t, m in self._index.items() if m["source_type"] == source_type]
        return list(self._index.keys())

    def load_from_duckdb(self) -> None:
        """Load all existing DuckDB tables into the registry.

        Called during bootstrap after demo data is imported.
        Tables not yet registered get auto-registered as 'demo'.
        """
        tables = self._engine.tables()
        for table_name in tables:
            if table_name not in self._index:
                self._index[table_name] = {
                    "display_name": table_name,
                    "source_type": "demo",
                    "session_id": None,
                    "columns_meta": [],
                }
        logger.info({"event": "registry_loaded", "count": len(self._index)})

    def _build_table_schema(self, table_name: str, meta: dict) -> Optional[TableSchema]:
        """Build a TableSchema by profiling the DuckDB table."""
        try:
            # Use profiler if available
            if self._profiler:
                profile = self._profiler.profile(table_name)
                columns = []
                for col in profile["columns"]:
                    columns.append(ColumnSchema(
                        name=col["name"],
                        data_type=col["type"],
                        semantic_type=col["semantic_type"],
                        null_ratio=col["null_ratio"],
                        unique_count=col["unique_count"],
                        min_value=col.get("min"),
                        max_value=col.get("max"),
                        top_values=col.get("top_values", []),
                    ))
                return TableSchema(
                    table_name=table_name,
                    display_name=meta.get("display_name", table_name),
                    source_type=meta.get("source_type", "unknown"),
                    session_id=meta.get("session_id"),
                    row_count=profile.get("row_count", 0),
                    columns=columns,
                )
            else:
                # Fallback: basic schema without profiling
                desc = self._engine.execute(f'DESCRIBE "{table_name}"').fetchall()
                columns = [
                    ColumnSchema(name=col[0], data_type=col[1], semantic_type="text")
                    for col in desc
                ]
                return TableSchema(
                    table_name=table_name,
                    display_name=meta.get("display_name", table_name),
                    source_type=meta.get("source_type", "unknown"),
                    session_id=meta.get("session_id"),
                    columns=columns,
                )
        except Exception as exc:
            logger.error({"event": "schema_build_failed", "table": table_name, "error": str(exc)})
            return None
