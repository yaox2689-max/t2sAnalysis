"""Tests for DuckDBExecutor — execution, errors, sanitisation, truncation."""

from unittest.mock import MagicMock

import pandas as pd
import pytest

from app.tools.duckdb_executor import (
    DuckDBExecutionError,
    DuckDBExecutor,
    DuckDBWriteBlockedError,
)


@pytest.fixture
def mock_engine():
    """Mock DuckDB engine."""
    engine = MagicMock()
    return engine


@pytest.fixture
def executor(mock_engine):
    """Create a DuckDBExecutor with a mocked engine."""
    return DuckDBExecutor(
        duckdb_engine=mock_engine,
        max_rows=100,
        timeout=10,
    )


# ── Normal execution ──────────────────────────────────────


class TestNormalExecution:
    async def test_returns_query_result(self, executor, mock_engine):
        """Normal SQL returns a QueryResult."""
        df = pd.DataFrame({"id": [1, 2], "name": ["Alice", "Bob"]})
        mock_engine.execute.return_value.fetchdf.return_value = df

        result = await executor.execute("SELECT * FROM orders")
        assert result.columns == ["id", "name"]
        assert len(result.rows) == 2
        assert result.elapsed_ms >= 0

    async def test_empty_result(self, executor, mock_engine):
        """SQL returning no rows returns empty QueryResult."""
        df = pd.DataFrame({"id": pd.Series([], dtype="int64")})
        mock_engine.execute.return_value.fetchdf.return_value = df

        result = await executor.execute("SELECT * FROM orders WHERE 1=0")
        assert result.columns == ["id"]
        assert len(result.rows) == 0


# ── Write operations ──────────────────────────────────────


class TestWriteBlocked:
    async def test_insert_raises_error(self, executor):
        """INSERT is blocked."""
        with pytest.raises(DuckDBWriteBlockedError):
            await executor.execute("INSERT INTO orders (id) VALUES (1)")

    async def test_delete_raises_error(self, executor):
        """DELETE is blocked."""
        with pytest.raises(DuckDBWriteBlockedError):
            await executor.execute("DELETE FROM orders WHERE id = 1")

    async def test_drop_raises_error(self, executor):
        """DROP is blocked."""
        with pytest.raises(DuckDBWriteBlockedError):
            await executor.execute("DROP TABLE orders")

    async def test_update_raises_error(self, executor):
        """UPDATE is blocked."""
        with pytest.raises(DuckDBWriteBlockedError):
            await executor.execute("UPDATE orders SET status = 'x' WHERE id = 1")


# ── Timeout ───────────────────────────────────────────────


class TestTimeout:
    async def test_timeout_raises_execution_error(self, mock_engine):
        """Timeout during execution raises DuckDBExecutionError."""
        executor = DuckDBExecutor(
            duckdb_engine=mock_engine,
            max_rows=100,
            timeout=0.001,  # 1ms timeout
        )

        def slow_query(sql):
            import time
            time.sleep(1)

        mock_engine.execute.return_value.fetchdf = slow_query

        with pytest.raises(DuckDBExecutionError, match="timed out"):
            await executor.execute("SELECT * FROM huge_table")

    async def test_engine_error_raises_execution_error(self, executor, mock_engine):
        """Database error raises DuckDBExecutionError."""
        mock_engine.execute.side_effect = Exception("table not found")

        with pytest.raises(DuckDBExecutionError):
            await executor.execute("SELECT * FROM nonexistent")


# ── NaN sanitisation ──────────────────────────────────────


class TestNaNSanitisation:
    async def test_nan_converted_to_none(self, executor, mock_engine):
        """NaN values in the result are sanitised to None."""
        df = pd.DataFrame({"value": [1.0, float("nan"), 3.0]})
        mock_engine.execute.return_value.fetchdf.return_value = df

        result = await executor.execute("SELECT * FROM test")
        assert result.rows[0]["value"] == 1.0
        assert result.rows[1]["value"] is None
        assert result.rows[2]["value"] == 3.0

    async def test_inf_converted_to_none(self, executor, mock_engine):
        """Inf values in the result are sanitised to None."""
        df = pd.DataFrame({"value": [float("inf"), float("-inf")]})
        mock_engine.execute.return_value.fetchdf.return_value = df

        result = await executor.execute("SELECT * FROM test")
        assert result.rows[0]["value"] is None
        assert result.rows[1]["value"] is None


# ── Truncation ────────────────────────────────────────────


class TestTruncation:
    async def test_rows_truncated_to_max_rows(self, mock_engine):
        """Rows exceeding max_rows are truncated."""
        executor = DuckDBExecutor(
            duckdb_engine=mock_engine,
            max_rows=5,
            timeout=10,
        )
        df = pd.DataFrame({"id": list(range(20))})
        mock_engine.execute.return_value.fetchdf.return_value = df

        result = await executor.execute("SELECT * FROM big_table")
        assert len(result.rows) == 5
        assert result.truncated is True

    async def test_rows_not_truncated_under_limit(self, executor, mock_engine):
        """Rows within max_rows are not truncated."""
        df = pd.DataFrame({"id": list(range(3))})
        mock_engine.execute.return_value.fetchdf.return_value = df

        result = await executor.execute("SELECT * FROM small_table")
        assert len(result.rows) == 3
        assert result.truncated is False


# ── preview_table ─────────────────────────────────────────


class TestPreviewTable:
    async def test_preview_returns_dataframe(self, executor, mock_engine):
        """preview_table returns a DataFrame."""
        df = pd.DataFrame({"id": [1, 2], "val": ["a", "b"]})
        mock_engine.execute.return_value.fetchdf.return_value = df

        result = await executor.preview_table("orders", limit=2)
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2

    async def test_preview_uses_limit(self, executor, mock_engine):
        """preview_table passes limit to SQL."""
        df = pd.DataFrame({"id": [1]})
        mock_engine.execute.return_value.fetchdf.return_value = df

        await executor.preview_table("orders", limit=1)
        call_sql = mock_engine.execute.call_args[0][0]
        assert "LIMIT 1" in call_sql
