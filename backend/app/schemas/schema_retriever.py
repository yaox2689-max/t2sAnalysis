"""Schema Retriever — dual-path retrieval (FAISS + keyword) with FK expansion.

This is the main entry point for finding relevant schema information
given a user question. It combines:

1. FAISS vector search (semantic matching on table/column descriptions)
2. Keyword matching (direct name overlap)
3. FK expansion (include related tables)

The result is a deduplicated, token-budgeted SchemaContext ready for
SQLGenerator's prompt.

Usage:
    from app.schemas.schema_retriever import SchemaRetriever

    retriever = SchemaRetriever(schema_index, schema_repository)
    context = await retriever.retrieve("最近30天各品类销售额趋势")
"""

from app.models.task import SchemaContext
from app.schemas.schema_index import SchemaIndex

# ── Defaults ────────────────────────────────────────────

MAX_SCHEMA_TOKENS: int = 2500
"""Upper bound on estimated schema context tokens passed to the LLM."""

# ── Keyword hints — map Chinese business terms to table names ──
_KEYWORD_MAP: dict[str, list[str]] = {
    "订单": ["orders"],
    "销量": ["order_items"],
    "销售额": ["payments", "orders"],
    "收入": ["payments", "orders"],
    "客户": ["customers"],
    "用户": ["customers"],
    "商品": ["products"],
    "品类": ["products", "product_category"],
    "分类": ["product_category"],
    "支付": ["payments"],
    "付款": ["payments"],
    "退款": ["reviews", "orders"],
    "评价": ["reviews"],
    "评分": ["reviews"],
    "商家": ["sellers"],
    "卖家": ["sellers"],
    "配送": ["order_items"],
    "物流": ["order_items"],
}


def _estimate_tokens(text: str) -> int:
    """Rough token estimate (≈ characters / 4 for mixed CN/EN text)."""
    return len(text) // 4 + 1


class SchemaRetriever:
    """Retrieve relevant schema context for a user question."""

    def __init__(
        self,
        schema_index: SchemaIndex,
        schema_repository: object,
    ) -> None:
        self._index = schema_index
        self._repo = schema_repository

    async def retrieve(
        self,
        question: str,
        top_k_tables: int = 3,
        top_k_columns: int = 5,
        max_tokens: int = MAX_SCHEMA_TOKENS,
    ) -> SchemaContext:
        """Retrieve SchemaContext for a question.

        Steps:
        1. Embed the question.
        2. FAISS vector search (tables + columns).
        3. Keyword match.
        4. FK expansion.
        5. Deduplicate and apply token budget.
        6. Build SchemaContext from repository.
        """
        query_vec = await self._embed_question(question)

        candidates = self._search_vector(query_vec, top_k_tables, top_k_columns)
        candidates.update(self._search_keyword(question))

        fks = await self._repo.get_foreign_keys()
        fk_map = self._build_fk_map(fks)
        expanded = self._expand_fk(candidates, fk_map)

        return await self._build_context(expanded, fks, max_tokens=max_tokens)

    # ── Retrieval steps ─────────────────────────────────

    async def _embed_question(self, question: str) -> list[float]:
        """Embed question via SchemaIndex."""
        return await self._index.embed_query(question)

    def _search_vector(
        self,
        query_vec: list[float],
        top_k_tables: int,
        top_k_columns: int,
    ) -> set[str]:
        """FAISS vector search — collect candidate table names."""
        table_matches = self._index.search_tables(query_vec, top_k=top_k_tables)
        column_matches = self._index.search_columns(query_vec, top_k=top_k_columns)

        tables: set[str] = set()
        for meta, _score in table_matches:
            tables.add(meta.name)
        for meta, _score in column_matches:
            tables.add(meta.table)
        return tables

    def _search_keyword(self, question: str) -> set[str]:
        """Keyword matching — map Chinese business terms to table names."""
        tables: set[str] = set()
        for keyword, table_names in _KEYWORD_MAP.items():
            if keyword in question:
                tables.update(table_names)
        return tables

    @staticmethod
    def _expand_fk(
        candidates: set[str],
        fk_map: dict[str, set[str]],
    ) -> set[str]:
        """FK expansion — include tables related via foreign keys."""
        expanded: set[str] = set(candidates)
        for t in candidates:
            if t in fk_map:
                expanded.update(fk_map[t])
        return expanded

    # ── Context building ────────────────────────────────

    async def _build_context(
        self,
        tables: set[str],
        fks: list[dict],
        max_tokens: int,
    ) -> SchemaContext:
        """Fetch metadata and apply token budget.

        Tables are processed in sorted order; once the estimated token
        total exceeds *max_tokens* any remaining tables are dropped.
        """
        columns_dict: dict[str, list[dict]] = {}
        sample_dict: dict[str, list[dict]] = {}
        relationships: list[str] = []
        estimated: int = 0
        included: list[str] = []

        for table in sorted(tables):
            cols = await self._repo.get_columns(table)
            rows: list[dict] = []

            try:
                raw = await self._repo.get_sample_rows(table)
                rows = raw or []
            except Exception:
                pass

            # Rough token budget for this table
            table_text = table
            for c in cols:
                table_text += c.get("column_name", "") + c.get("column_comment", "")
            for r in rows:
                table_text += "".join(str(v) for v in r.values())
            table_est = _estimate_tokens(table_text)

            if estimated + table_est > max_tokens and included:
                break  # don't break on the first table

            estimated += table_est
            included.append(table)
            columns_dict[table] = cols
            if rows:
                sample_dict[table] = rows

        # FK relationships (only for included tables)
        for fk in fks:
            src = fk["table_name"]
            ref = fk["ref_table_name"]
            if src in included or ref in included:
                relationships.append(
                    f"{fk['table_name']}.{fk['column_name']}"
                    f" → {fk['ref_table_name']}.{fk['ref_column_name']}"
                )

        return SchemaContext(
            tables=included,
            columns=columns_dict,
            relationships=relationships,
            sample_rows=sample_dict,
        )

    # ── Helpers ─────────────────────────────────────────

    @staticmethod
    def _build_fk_map(fks: list[dict]) -> dict[str, set[str]]:
        """Build a map of each table → its FK-related tables."""
        fk_map: dict[str, set[str]] = {}
        for fk in fks:
            src = fk["table_name"]
            ref = fk["ref_table_name"]
            fk_map.setdefault(src, set()).add(ref)
            fk_map.setdefault(ref, set()).add(src)
        return fk_map
