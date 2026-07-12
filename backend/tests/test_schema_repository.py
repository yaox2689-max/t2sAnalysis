"""Tests for SchemaRepository."""

import pytest

from app.repositories.schema_repository import SchemaRepository
from app.core.database import db as _db


@pytest.fixture(scope="module")
def repo():
    _db.init()
    return SchemaRepository(_db)


@pytest.mark.asyncio
async def test_get_tables(repo):
    tables = await repo.get_tables()
    assert len(tables) >= 8
    names = {t["table_name"] for t in tables}
    assert "orders" in names
    assert "customers" in names
    assert "products" in names


@pytest.mark.asyncio
async def test_get_columns(repo):
    cols = await repo.get_columns("orders")
    names = {c["column_name"] for c in cols}
    assert "order_id" in names
    assert "customer_id" in names
    assert "order_status" in names
    assert all(c["data_type"] for c in cols)


@pytest.mark.asyncio
async def test_get_foreign_keys(repo):
    fks = await repo.get_foreign_keys()
    assert len(fks) >= 1
    orders_fk = [fk for fk in fks if fk["table_name"] == "orders"]
    assert any(fk["column_name"] == "customer_id" for fk in orders_fk)


@pytest.mark.asyncio
async def test_get_sample_rows_unknown_table(repo):
    with pytest.raises(ValueError, match="Unknown table"):
        await repo.get_sample_rows("nonexistent_table")


@pytest.mark.asyncio
async def test_get_sample_rows(repo):
    rows = await repo.get_sample_rows("orders", limit=2)
    assert isinstance(rows, list)
    assert len(rows) <= 2
