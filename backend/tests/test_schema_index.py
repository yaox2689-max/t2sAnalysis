"""Tests for SchemaIndex — build, search, persistence."""

import os
import tempfile

import pytest

from app.schemas.embedding import EmbeddingProvider
from app.schemas.schema_index import SchemaIndex


class FakeEmbedding(EmbeddingProvider):
    """Returns a deterministic 4-dim vector for each input."""

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[float(len(t)) / 100, 0.2, 0.3, 0.4] for t in texts]


class FakeRepository:
    """Returns hardcoded schema data without a database."""

    async def get_tables(self) -> list[dict]:
        return [
            {"table_name": "orders", "table_comment": "order data"},
            {"table_name": "customers", "table_comment": "customer info"},
        ]

    async def get_columns(self, table: str) -> list[dict]:
        if table == "orders":
            return [
                {"column_name": "id", "data_type": "int", "column_comment": "order id"},
                {"column_name": "total", "data_type": "decimal", "column_comment": ""},
            ]
        return [
            {"column_name": "id", "data_type": "int", "column_comment": ""},
            {"column_name": "name", "data_type": "varchar", "column_comment": "customer name"},
        ]


@pytest.fixture
def index():
    repo = FakeRepository()
    embed = FakeEmbedding()
    return SchemaIndex(repository=repo, embedding_provider=embed)


@pytest.mark.asyncio
async def test_build_populates_metadata(index):
    await index.build()
    assert len(index._table_metadata) == 2
    assert len(index._column_metadata) == 4


@pytest.mark.asyncio
async def test_build_deterministic_order(index):
    await index.build()
    names1 = [m.name for m in index._table_metadata]
    await index.build()
    names2 = [m.name for m in index._table_metadata]
    assert names1 == names2 == ["customers", "orders"]


@pytest.mark.asyncio
async def test_search_tables_returns_results(index):
    await index.build()
    query = [0.5, 0.2, 0.3, 0.4]
    results = index.search_tables(query, top_k=2)
    assert len(results) == 2
    assert isinstance(results[0][0].name, str)
    assert isinstance(results[0][1], float)


@pytest.mark.asyncio
async def test_search_columns_returns_results(index):
    await index.build()
    query = [0.5, 0.2, 0.3, 0.4]
    results = index.search_columns(query, top_k=3)
    assert len(results) == 3
    assert isinstance(results[0][0].column, str)


@pytest.mark.asyncio
async def test_save_and_load(index):
    await index.build()

    with tempfile.TemporaryDirectory() as tmpdir:
        index.save(tmpdir)

        fresh = SchemaIndex(
            repository=FakeRepository(),
            embedding_provider=FakeEmbedding(),
        )
        fresh.load(tmpdir)

        assert len(fresh._table_metadata) == 2
        assert len(fresh._column_metadata) == 4

        # Search still works after load
        results = fresh.search_tables([0.5, 0.2, 0.3, 0.4], top_k=1)
        assert len(results) == 1
