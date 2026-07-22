"""Tests for SafeExecutor — timeout, row limit, error wrapping."""

import asyncio

import pytest

from app.tools.sql_executor import SafeExecutor, ExecutionTimeoutError, DatabaseError
from app.core.database import db as _db


@pytest.fixture(scope="module")
def executor():
    _db.init()
    return SafeExecutor(_db)


@pytest.mark.asyncio
async def test_execute_normal(executor):
    """Normal query returns QueryResult with correct columns."""
    result = await executor.execute("SELECT 1 AS val, 'hello' AS msg")
    assert result.columns == ["val", "msg"]
    assert result.rows == [{"val": 1, "msg": "hello"}]
    assert result.truncated is False
    assert result.elapsed_ms > 0
    assert result.row_count == 1


@pytest.mark.asyncio
async def test_execute_empty(executor):
    """Query returning no rows produces empty result."""
    result = await executor.execute("SELECT * FROM orders WHERE 1=0")
    assert result.columns == []
    assert result.rows == []
    assert result.truncated is False
    assert result.row_count == 0


@pytest.mark.asyncio
async def test_execute_truncation(executor):
    """Result exceeding max_rows is truncated and flagged."""
    small = SafeExecutor(_db, max_rows=2)
    sql = "SELECT 1 AS n UNION ALL SELECT 2 UNION ALL SELECT 3 UNION ALL SELECT 4"
    result = await small.execute(sql)
    assert result.truncated is True
    assert len(result.rows) == 2
    assert result.row_count == 2


@pytest.mark.asyncio
async def test_execute_timeout(executor):
    """Query exceeding timeout raises TimeoutError."""
    slow = SafeExecutor(_db, timeout=1)
    with pytest.raises(ExecutionTimeoutError, match="timed out"):
        await slow.execute("SELECT SLEEP(2)")


@pytest.mark.asyncio
async def test_execute_syntax_error(executor):
    """Invalid SQL raises DatabaseError."""
    with pytest.raises(DatabaseError):
        await executor.execute("SELECT INVALID")
