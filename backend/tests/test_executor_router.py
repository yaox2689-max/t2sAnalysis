"""Tests for ExecutorRouter — routing, caching, edge cases."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.query import QueryResult
from app.tools.executor_router import ExecutorRouter, _extract_table_names

# ── _extract_table_names tests ────────────────────────────


class TestExtractTableNames:
    def test_simple_select(self):
        assert _extract_table_names("SELECT * FROM orders") == ["orders"]

    def test_join(self):
        tables = _extract_table_names(
            "SELECT o.id FROM orders o JOIN customers c ON o.customer_id = c.id"
        )
        assert "orders" in tables
        assert "customers" in tables

    def test_invalid_sql(self):
        assert _extract_table_names("NOT VALID SQL !!!") == []

    def test_empty_string(self):
        assert _extract_table_names("") == []


# ── ExecutorRouter tests ──────────────────────────────────


@pytest.fixture
def duckdb_executor():
    """Mock DuckDB executor."""
    exe = AsyncMock()
    exe.execute.return_value = QueryResult(
        columns=["id", "total"],
        rows=[{"id": 1, "total": 100}],
    )
    return exe


@pytest.fixture
def external_executor():
    """Mock External DB executor."""
    exe = AsyncMock()
    exe.execute.return_value = QueryResult(
        columns=["id", "name"],
        rows=[{"id": 1, "name": "Alice"}],
    )
    return exe


@pytest.fixture
def registry():
    """Mock DatasetRegistry."""
    reg = MagicMock()
    reg.get_meta.return_value = None
    return reg


@pytest.fixture
def cache():
    """Mock QueryCache."""
    c = AsyncMock()
    c.get.return_value = None
    return c


@pytest.fixture
def connection_store():
    """Mock connection store."""
    store = AsyncMock()
    store.get_config.return_value = {"host": "localhost", "port": 3306}
    return store


@pytest.fixture
def router(duckdb_executor, registry, external_executor, connection_store, cache):
    """Create an ExecutorRouter with mocked dependencies."""
    return ExecutorRouter(
        duckdb_executor=duckdb_executor,
        registry=registry,
        external_executor=external_executor,
        connection_store=connection_store,
        cache=cache,
    )


# ── Routing tests ─────────────────────────────────────────


class TestRouting:
    async def test_duckdb_table_routes_to_duckdb(self, router, duckdb_executor):
        """Table not registered as mysql → goes to DuckDB."""
        result = await router.execute("SELECT * FROM orders")
        duckdb_executor.execute.assert_called_once()
        assert result.columns == ["id", "total"]

    async def test_mysql_table_routes_to_external(
        self, router, registry, external_executor, connection_store
    ):
        """Table registered as mysql → goes to ExternalDB."""
        registry.get_meta.return_value = {
            "source_type": "mysql",
            "connection_id": "conn_123",
        }
        result = await router.execute("SELECT * FROM remote_orders")
        external_executor.execute.assert_called_once()
        assert result.columns == ["id", "name"]

    async def test_mysql_no_connection_falls_back_to_duckdb(
        self, router, registry, duckdb_executor
    ):
        """MySQL table without connection_id → falls back to DuckDB."""
        registry.get_meta.return_value = {"source_type": "mysql"}
        await router.execute("SELECT * FROM orders")
        duckdb_executor.execute.assert_called_once()

    async def test_unknown_table_uses_duckdb_by_default(
        self, router, registry, duckdb_executor
    ):
        """Unknown table (get_meta returns None) → DuckDB."""
        registry.get_meta.return_value = None
        await router.execute("SELECT * FROM unknown_table")
        duckdb_executor.execute.assert_called_once()


# ── Cache tests ───────────────────────────────────────────


class TestCaching:
    async def test_cache_hit_returns_cached(self, router, cache):
        """If cache has the result, return it without executing."""
        cached = QueryResult(columns=["id"], rows=[{"id": 999}])
        cache.get.return_value = cached
        result = await router.execute("SELECT * FROM orders")
        assert result.rows[0]["id"] == 999

    async def test_cache_miss_executes_and_caches(
        self, router, cache, duckdb_executor
    ):
        """On cache miss, execute and store result."""
        cache.get.return_value = None
        result = await router.execute("SELECT * FROM orders")
        cache.set.assert_called_once()
        assert result.columns == ["id", "total"]

    async def test_no_cache_still_executes(self, router, cache, duckdb_executor):
        """If no cache, execute normally."""
        router._cache = None
        result = await router.execute("SELECT * FROM orders")
        duckdb_executor.execute.assert_called_once()
        assert result is not None


# ── Empty SQL ─────────────────────────────────────────────


class TestEdgeCases:
    async def test_empty_sql_returns_empty_tables(self):
        """Empty SQL should extract no table names and fall through to DuckDB."""
        exe = AsyncMock()
        exe.execute.return_value = QueryResult(columns=[], rows=[])
        router = ExecutorRouter(
            duckdb_executor=exe,
            registry=MagicMock(),
            external_executor=AsyncMock(),
        )
        result = await router.execute("")
        exe.execute.assert_called_once()
        assert result.columns == []
