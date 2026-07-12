"""Tests for SchemaRetriever — dual-path retrieval, FK expansion, token budget."""

import pytest

from app.schemas.schema_retriever import SchemaRetriever


class FakeEmbed:
    """Returns a simple deterministic vector."""
    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[float(len(t)) / 100, 0.2, 0.3, 0.4] for t in texts]


class FakeIndex:
    """Minimal FAISS index mock — hardcoded results."""
    _embed = FakeEmbed()

    def search_tables(self, query_vec, top_k=3):
        return []  # No results — rely on keyword path

    def search_columns(self, query_vec, top_k=5):
        return []

    async def embed_query(self, text: str) -> list[float]:
        return (await self._embed.embed([text]))[0]


class FakeRepo:
    async def get_tables(self) -> list[dict]:
        return [{"table_name": "orders"}]

    async def get_columns(self, table: str) -> list[dict]:
        if table == "orders":
            return [
                {"column_name": "id", "data_type": "int", "column_comment": ""},
                {"column_name": "total", "data_type": "decimal", "column_comment": ""},
            ]
        if table == "payments":
            return [
                {"column_name": "order_id", "data_type": "int", "column_comment": ""},
                {"column_name": "value", "data_type": "decimal", "column_comment": ""},
            ]
        return []

    async def get_foreign_keys(self) -> list[dict]:
        return [
            {"table_name": "payments", "column_name": "order_id",
             "ref_table_name": "orders", "ref_column_name": "id"},
        ]

    async def get_sample_rows(self, table: str, limit=3) -> list[dict]:
        return [{"id": 1}]


@pytest.fixture
def retriever():
    index = FakeIndex()
    repo = FakeRepo()
    return SchemaRetriever(schema_index=index, schema_repository=repo)


@pytest.mark.asyncio
async def test_retrieve_by_keyword(retriever):
    """销售额 should match payments + orders via keyword, then FK expand orders."""
    context = await retriever.retrieve("最近30天各品类销售额趋势")
    assert "orders" in context.tables
    assert "payments" in context.tables


@pytest.mark.asyncio
async def test_retrieve_returns_schema_context(retriever):
    context = await retriever.retrieve("客户订单")
    assert "customers" in context.tables
    assert hasattr(context, "columns")
    assert hasattr(context, "relationships")


@pytest.mark.asyncio
async def test_retrieve_fk_expansion(retriever):
    """payments has FK → orders, so orders should be added."""
    context = await retriever.retrieve("支付")
    assert "payments" in context.tables
    assert "orders" in context.tables  # via FK expansion


@pytest.mark.asyncio
async def test_retrieve_includes_relationships(retriever):
    context = await retriever.retrieve("支付订单")
    fk_text = "\n".join(context.relationships)
    assert "payments.order_id" in fk_text
    assert "orders.id" in fk_text


@pytest.mark.asyncio
async def test_retrieve_no_match(retriever):
    """No matching keywords returns empty result."""
    context = await retriever.retrieve("不相关的内容abcxyz")
    assert context.tables == []
    assert context.columns == {}


@pytest.mark.asyncio
async def test_token_budget_excludes_overflow(retriever):
    """With max_tokens=1 the second table should be dropped."""
    context = await retriever.retrieve("支付", max_tokens=1)
    # orders sorts first and always fits; payments should be excluded
    assert "orders" in context.tables
    assert "payments" not in context.tables


@pytest.mark.asyncio
async def test_token_budget_includes_all(retriever):
    """A generous budget keeps all matched tables."""
    context = await retriever.retrieve("支付", max_tokens=10_000)
    assert "orders" in context.tables
    assert "payments" in context.tables
