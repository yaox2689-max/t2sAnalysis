"""FAISS-based vector index for tables and columns.

Builds and persists two FAISS indexes:
- Tables: one vector per table (name + comment)
- Columns: one vector per column (column name + comment + table name)

This index is consumed by SchemaRetriever (PR #12) to find relevant
schema information for a user question.

Usage:
    from app.schemas.schema_index import SchemaIndex
    from app.schemas.embedding import EmbeddingProvider

    index = SchemaIndex(repository, embedding_provider)
    await index.build()
    index.save("path/to/index_dir")
    index.load("path/to/index_dir")
    results = index.search_tables("sales trend", top_k=3)
"""

import json
import os

import numpy as np

from app.schemas.embedding import EmbeddingProvider
from app.schemas.models import ColumnMetadata, TableMetadata

try:
    import faiss
except ImportError:
    faiss = None  # type: ignore[assignment]


class SchemaIndex:
    """FAISS vector index for database schema metadata."""

    def __init__(
        self,
        repository: object,
        embedding_provider: EmbeddingProvider,
    ) -> None:
        self._repo = repository
        self._embed = embedding_provider
        self._table_index: object = None
        self._column_index: object = None
        self._table_metadata: list[TableMetadata] = []
        self._column_metadata: list[ColumnMetadata] = []

    async def build(self) -> None:
        """Build both indexes from the current schema.

        Metadata order is sorted alphabetically to ensure deterministic
        index construction across rebuilds.
        """
        tables = sorted(await self._repo.get_tables(), key=lambda t: t["table_name"])
        table_texts: list[str] = []
        self._table_metadata = []

        for t in tables:
            name = t["table_name"]
            comment = t.get("table_comment", "")
            table_texts.append(f"{name} {comment}".strip())
            self._table_metadata.append(TableMetadata(name=name, comment=comment))

        # Build table FAISS index
        table_vecs = await self._embed.embed(table_texts)
        self._table_index = self._build_faiss(table_vecs)

        # Build column FAISS index
        column_texts: list[str] = []
        self._column_metadata = []

        for t in tables:
            name = t["table_name"]
            cols = sorted(
                await self._repo.get_columns(name),
                key=lambda c: c["column_name"],
            )
            for c in cols:
                col_name = c["column_name"]
                col_type = c.get("data_type", "")
                col_comment = c.get("column_comment", "")
                column_texts.append(
                    f"{name}.{col_name} ({col_type}) {col_comment}".strip()
                )
                self._column_metadata.append(
                    ColumnMetadata(
                        table=name,
                        column=col_name,
                        data_type=col_type,
                        comment=col_comment,
                    )
                )

        col_vecs = await self._embed.embed(column_texts)
        self._column_index = self._build_faiss(col_vecs)

    # ── Search ───────────────────────────────────────────

    async def embed_query(self, text: str) -> list[float]:
        """Embed a single query string into a float vector."""
        return (await self._embed.embed([text]))[0]

    def search_tables(
        self, query_vec: list[float], top_k: int = 3
    ) -> list[tuple[TableMetadata, float]]:
        """Search the table index by query vector."""
        if self._table_index is None:
            return []
        return self._search(self._table_index, self._table_metadata, query_vec, top_k)

    def search_columns(
        self, query_vec: list[float], top_k: int = 5
    ) -> list[tuple[ColumnMetadata, float]]:
        """Search the column index by query vector."""
        if self._column_index is None:
            return []
        return self._search(self._column_index, self._column_metadata, query_vec, top_k)

    # ── Persistence ──────────────────────────────────────

    def save(self, index_dir: str) -> None:
        """Persist indexes and metadata to disk."""
        os.makedirs(index_dir, exist_ok=True)

        if self._table_index is not None:
            faiss.write_index(self._table_index, os.path.join(index_dir, "tables.faiss"))
        if self._column_index is not None:
            faiss.write_index(self._column_index, os.path.join(index_dir, "columns.faiss"))

        with open(os.path.join(index_dir, "tables.json"), "w", encoding="utf-8") as f:
            json.dump([m.model_dump() for m in self._table_metadata], f)
        with open(os.path.join(index_dir, "columns.json"), "w", encoding="utf-8") as f:
            json.dump([m.model_dump() for m in self._column_metadata], f)

    def load(self, index_dir: str) -> None:
        """Load indexes and metadata from disk."""
        table_path = os.path.join(index_dir, "tables.faiss")
        col_path = os.path.join(index_dir, "columns.faiss")

        if os.path.exists(table_path):
            self._table_index = faiss.read_index(table_path)
        if os.path.exists(col_path):
            self._column_index = faiss.read_index(col_path)

        tables_json = os.path.join(index_dir, "tables.json")
        columns_json = os.path.join(index_dir, "columns.json")

        # Fallback: migrate from legacy pickle files
        tables_pkl = os.path.join(index_dir, "tables.pkl")
        columns_pkl = os.path.join(index_dir, "columns.pkl")

        if os.path.exists(tables_json):
            with open(tables_json, "r", encoding="utf-8") as f:
                self._table_metadata = [TableMetadata(**m) for m in json.load(f)]
        elif os.path.exists(tables_pkl):
            import pickle as _pickle
            with open(tables_pkl, "rb") as f:
                self._table_metadata = _pickle.load(f)

        if os.path.exists(columns_json):
            with open(columns_json, "r", encoding="utf-8") as f:
                self._column_metadata = [ColumnMetadata(**m) for m in json.load(f)]
        elif os.path.exists(columns_pkl):
            import pickle as _pickle
            with open(columns_pkl, "rb") as f:
                self._column_metadata = _pickle.load(f)

    # ── Internals ────────────────────────────────────────

    @staticmethod
    def _build_faiss(vectors: list[list[float]]) -> object:
        """Build a flat (brute-force) FAISS index from vectors."""
        dim = len(vectors[0]) if vectors else 0
        if dim == 0:
            index = faiss.IndexFlatIP(1)  # dummy
            return index
        mat = np.array(vectors, dtype=np.float32)
        index = faiss.IndexFlatIP(dim)
        index.add(mat)
        return index

    @staticmethod
    def _search(
        index: object,
        metadata: list,
        query_vec: list[float],
        top_k: int,
    ) -> list:
        """Run a FAISS search and attach metadata + scores."""
        n = len(metadata)
        k = min(top_k, n)
        mat = np.array([query_vec], dtype=np.float32)
        scores, indices = index.search(mat, k)  # type: ignore[union-attr]
        results = []
        for i, idx in enumerate(indices[0]):
            results.append((metadata[idx], float(scores[0][i])))
        return results
