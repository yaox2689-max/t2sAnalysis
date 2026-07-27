"""Tests for DatasetRegistry — register, catalog, metadata, listing."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.dataset_registry import DatasetRegistry


@pytest.fixture
def mock_engine():
    """Mock DuckDB engine."""
    return MagicMock()


@pytest.fixture
def mock_profiler():
    """Mock SchemaProfiler with async profile method."""
    profiler = AsyncMock()
    profiler.profile.return_value = {
        "row_count": 100,
        "columns": [
            {
                "name": "id",
                "type": "int",
                "semantic_type": "id",
                "null_ratio": 0.0,
                "unique_count": 100,
                "min": "1",
                "max": "100",
                "top_values": ["1", "2", "3"],
            },
            {
                "name": "amount",
                "type": "decimal",
                "semantic_type": "metric",
                "null_ratio": 0.05,
                "unique_count": 80,
                "min": "0.0",
                "max": "999.9",
            },
        ],
    }
    return profiler


@pytest.fixture
def registry(mock_engine, mock_profiler):
    """Create a DatasetRegistry with mocked engine and profiler."""
    return DatasetRegistry(mock_engine, mock_profiler)


# ── Register / Unregister lifecycle ───────────────────────


class TestLifecycle:
    def test_register_adds_to_index(self, registry):
        """register() adds a table to the in-memory index."""
        registry.register(
            table_name="orders",
            display_name="Orders",
            source_type="excel",
            session_id="ses_1",
            user_id="usr_1",
        )
        meta = registry.get_meta("orders")
        assert meta is not None
        assert meta["display_name"] == "Orders"
        assert meta["source_type"] == "excel"

    def test_unregister_removes_from_index(self, registry):
        """unregister() removes a table from the index."""
        registry.register("temp_table", "Temp", "csv")
        registry.unregister("temp_table")
        assert registry.get_meta("temp_table") is None

    def test_unregister_nonexistent_is_safe(self, registry):
        """unregister() on a non-existent table does not raise."""
        registry.unregister("nonexistent")


# ── get_catalog ───────────────────────────────────────────


class TestGetCatalog:
    async def test_filters_by_user_id(self, registry):
        """Catalog filters tables by user_id."""
        registry.register("t1", "T1", "excel", user_id="usr_1")
        registry.register("t2", "T2", "excel", user_id="usr_2")
        catalog = await registry.get_catalog(user_id="usr_1")
        assert len(catalog.tables) == 1
        assert catalog.tables[0].table_name == "t1"

    async def test_filters_by_session_id(self, registry):
        """Catalog filters tables by session_id."""
        registry.register("t1", "T1", "excel", session_id="ses_1")
        registry.register("t2", "T2", "excel", session_id="ses_2")
        catalog = await registry.get_catalog(session_id="ses_1")
        assert len(catalog.tables) == 1
        assert catalog.tables[0].table_name == "t1"

    async def test_top_k_limits_results(self, registry):
        """top_k limits the number of tables returned."""
        for i in range(5):
            registry.register(f"t{i}", f"T{i}", "excel")
        catalog = await registry.get_catalog(top_k=3)
        assert len(catalog.tables) == 3


# ── get_table_schema ──────────────────────────────────────


class TestGetTableSchema:
    async def test_returns_correct_structure(self, registry):
        """get_table_schema returns a TableSchema with profiled columns."""
        registry.register(
            "orders",
            "Orders",
            "excel",
            session_id="ses_1",
            user_id="usr_1",
            columns_meta=[
                {"name": "id", "original_name": "ID"},
            ],
        )
        schema = await registry.get_table_schema("orders")
        assert schema is not None
        assert schema.table_name == "orders"
        assert schema.display_name == "Orders"
        assert schema.source_type == "excel"
        assert schema.row_count == 100
        assert len(schema.columns) == 2
        assert schema.columns[0].name == "id"
        assert schema.columns[0].original_name == "ID"

    async def test_nonexistent_returns_none(self, registry):
        """get_table_schema returns None for unregistered table."""
        assert await registry.get_table_schema("nonexistent") is None


# ── list_tables ───────────────────────────────────────────


class TestListTables:
    def test_list_all(self, registry):
        """list_tables returns all table names when no filter."""
        registry.register("t1", "T1", "excel")
        registry.register("t2", "T2", "csv")
        registry.register("t3", "T3", "mysql")
        tables = registry.list_tables()
        assert set(tables) == {"t1", "t2", "t3"}

    def test_list_with_source_type_filter(self, registry):
        """list_tables filters by source_type."""
        registry.register("t1", "T1", "excel")
        registry.register("t2", "T2", "csv")
        registry.register("t3", "T3", "csv")
        tables = registry.list_tables(source_type="csv")
        assert set(tables) == {"t2", "t3"}


# ── get_meta / set_meta ───────────────────────────────────


class TestMetaAccess:
    def test_get_meta_returns_dict(self, registry):
        """get_meta returns the metadata dict."""
        registry.register("t1", "T1", "excel")
        meta = registry.get_meta("t1")
        assert meta is not None
        assert meta["source_type"] == "excel"

    def test_get_meta_nonexistent_returns_none(self, registry):
        """get_meta returns None for unregistered table."""
        assert registry.get_meta("nonexistent") is None

    def test_set_meta_updates_field(self, registry):
        """set_meta sets a field on existing table."""
        registry.register("t1", "T1", "excel")
        registry.set_meta("t1", "source_type", "mysql")
        assert registry.get_meta("t1")["source_type"] == "mysql"

    def test_set_meta_nonexistent_is_safe(self, registry):
        """set_meta on non-existent table does not raise."""
        registry.set_meta("nonexistent", "key", "value")


# ── count_external_tables / iter_by_connection ────────────


class TestConnectionMethods:
    def test_count_external_tables(self, registry):
        """count_external_tables counts tables for a connection."""
        registry.register("t1", "T1", "mysql")
        registry.set_meta("t1", "connection_id", "conn_1")
        registry.register("t2", "T2", "mysql")
        registry.set_meta("t2", "connection_id", "conn_1")
        registry.register("t3", "T3", "mysql")
        registry.set_meta("t3", "connection_id", "conn_2")

        assert registry.count_external_tables("conn_1") == 2
        assert registry.count_external_tables("conn_2") == 1
        assert registry.count_external_tables("conn_999") == 0

    def test_iter_by_connection(self, registry):
        """iter_by_connection yields table names for a connection."""
        registry.register("t1", "T1", "mysql")
        registry.set_meta("t1", "connection_id", "conn_1")
        registry.register("t2", "T2", "mysql")
        registry.set_meta("t2", "connection_id", "conn_1")
        registry.register("t3", "T3", "mysql")
        registry.set_meta("t3", "connection_id", "conn_2")

        tables = list(registry.iter_by_connection("conn_1"))
        assert set(tables) == {"t1", "t2"}
