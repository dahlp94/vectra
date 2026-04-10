"""Main retrieval orchestration layer for query embedding + vector search."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.embeddings.provider import EmbeddingProvider, OpenAIEmbeddingProvider
from app.embeddings.service import EmbeddingService
from app.retrieval.filters import normalize_metadata_filters
from app.retrieval.vector_store import similarity_search
from app.schemas.query import QueryResponse, QueryResult

DEFAULT_TOP_K = 5


def _build_embedding_provider() -> EmbeddingProvider:
    """Build retrieval-time embedding provider from application settings."""
    settings = get_settings()
    provider_name = settings.embedding_provider.lower().strip()

    if provider_name != "openai":
        raise ValueError(f"Unsupported embedding_provider: {settings.embedding_provider!r}")
    if not settings.openai_api_key:
        raise ValueError(
            "OPENAI_API_KEY is required when embedding_provider is set to 'openai'."
        )

    return OpenAIEmbeddingProvider(
        api_key=settings.openai_api_key,
        model=settings.embedding_model,
    )


class RetrievalService:
    """Orchestrates query embedding, metadata filter prep, and vector search."""

    def __init__(self, session: Session, embedding_service: EmbeddingService | None = None) -> None:
        """
        Initialize retrieval service.

        Args:
            session: Open SQLAlchemy session.
            embedding_service: Optional preconfigured embedding service (useful in tests).
        """
        self._session = session
        self._embedding_service = embedding_service or EmbeddingService(provider=_build_embedding_provider())

    def retrieve(
        self,
        query: str,
        top_k: int | None = None,
        filters: Mapping[str, Any] | None = None,
    ) -> QueryResponse:
        """
        Retrieve top-k semantically similar chunks for a natural-language query.

        Args:
            query: User's natural language query.
            top_k: Optional result limit (falls back to default).
            filters: Optional metadata filters (doc_type/team/source_path).

        Returns:
            Structured retrieval response with ranked chunk results.
        """
        normalized_query = query.strip()
        if not normalized_query:
            raise ValueError("query must be a non-empty string")

        resolved_top_k = top_k if top_k is not None else DEFAULT_TOP_K
        if resolved_top_k < 1:
            raise ValueError("top_k must be >= 1")

        query_vectors = self._embedding_service.embed_texts([normalized_query])
        if not query_vectors:
            return QueryResponse(results=[])

        normalized_filters = normalize_metadata_filters(filters)
        records = similarity_search(
            session=self._session,
            query_embedding=query_vectors[0],
            top_k=resolved_top_k,
            metadata_filters=normalized_filters,
        )

        results = [QueryResult(**record) for record in records]
        return QueryResponse(results=results)
