"""Abstract interface for embedding providers.

SchemaIndex depends on this interface, not on any concrete
embedding implementation. Actual providers (OpenAI, sentence-transformers,
etc.) implement this protocol separately.

Usage:
    from app.schemas.embedding import EmbeddingProvider
"""

from typing import Protocol


class EmbeddingProvider(Protocol):
    """Protocol for text embedding providers.

    Implementations must provide an async embed method that accepts
    a list of strings and returns a list of float vectors.
    """

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of texts into float vectors."""
        ...
