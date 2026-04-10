"""Week 4 retrieval tests for embedding, vector search, and metadata filters."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import delete, func, select

from app.core.config import get_settings
from app.db.models import ChunkEmbedding, Document
from app.embeddings.provider import EmbeddingProvider
from app.embeddings.service import EmbeddingService
from app.ingestion.pipeline import ingest_folder
from app.retrieval.service import RetrievalService
from app.schemas.query import QueryResponse, QueryResult

REPO_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DOCS = REPO_ROOT / "data" / "sample_docs"


class _FakeIngestionEmbeddingProvider(EmbeddingProvider):
    """Deterministic ingestion provider that creates simple stored vectors."""

    def __init__(self, dimension: int) -> None:
        self._dimension = dimension

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for i, _ in enumerate(texts):
            base = float(i + 1)
            vectors.append([base] * self._dimension)
        return vectors


class _FakeQueryEmbeddingProvider(EmbeddingProvider):
    """Deterministic query provider used to test retrieval orchestration."""

    def __init__(self, dimension: int) -> None:
        self._dimension = dimension

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[1.0] * self._dimension for _ in texts]


@pytest.fixture
def db_session():
    """Open DB session and clean document data after each test."""
    try:
        from app.db.init_db import create_tables
        from app.db.session import get_session_factory
    except Exception as exc:  # pragma: no cover
        pytest.skip(f"Database stack unavailable: {exc}")

    try:
        get_settings()
        create_tables()
    except Exception as exc:
        pytest.skip(f"Database not reachable or migrations failed: {exc}")

    factory = get_session_factory()
    session = factory()
    try:
        yield session
    finally:
        session.execute(delete(Document))
        session.commit()
        session.close()


@pytest.fixture
def indexed_db_session(db_session, monkeypatch: pytest.MonkeyPatch):
    """Populate test DB with ingested chunks and stored embeddings."""
    if not SAMPLE_DOCS.is_dir():
        pytest.skip("data/sample_docs not present")

    settings = get_settings()
    monkeypatch.setattr(
        "app.ingestion.pipeline._build_embedding_provider",
        lambda: _FakeIngestionEmbeddingProvider(settings.embedding_dimension),
    )

    doc_count, chunk_count = ingest_folder(
        db_session,
        SAMPLE_DOCS,
        chunk_size=800,
        overlap=100,
    )
    db_session.commit()

    assert doc_count >= 1
    assert chunk_count >= 1
    yield db_session


def _build_retrieval_service(session) -> RetrievalService:
    """Create retrieval service with deterministic query embeddings."""
    settings = get_settings()
    query_embedding_service = EmbeddingService(
        provider=_FakeQueryEmbeddingProvider(settings.embedding_dimension),
    )
    return RetrievalService(session=session, embedding_service=query_embedding_service)


def test_retrieval_service_returns_ranked_results(indexed_db_session) -> None:
    """A natural-language query should return non-empty ranked retrieval results."""
    service = _build_retrieval_service(indexed_db_session)

    response = service.retrieve(query="how do we deploy services?", top_k=3)

    assert isinstance(response, QueryResponse)
    assert len(response.results) >= 1
    assert len(response.results) <= 3

    for result in response.results:
        assert isinstance(result, QueryResult)
        assert result.chunk_text.strip() != ""
        assert result.score <= 1.0

    scores = [item.score for item in response.results]
    assert scores == sorted(scores, reverse=True)


def test_retrieval_service_applies_doc_type_filter(indexed_db_session) -> None:
    """doc_type filter should constrain retrieval to matching document metadata."""
    service = _build_retrieval_service(indexed_db_session)

    doc_type = indexed_db_session.scalars(
        select(Document.doc_type).where(Document.doc_type.is_not(None))
    ).first()
    if doc_type is None:
        pytest.skip("No document with doc_type found for metadata filtering test")

    response = service.retrieve(
        query="incident response procedures",
        top_k=5,
        filters={"doc_type": doc_type},
    )

    assert len(response.results) >= 1

    matched_document_ids = {item.document_id for item in response.results}
    matched_doc_types = indexed_db_session.scalars(
        select(Document.doc_type).where(Document.id.in_(matched_document_ids))
    ).all()
    assert matched_doc_types
    assert all(value == doc_type for value in matched_doc_types)


def test_retrieval_response_structure(indexed_db_session) -> None:
    """Retrieval response should expose clean, typed result fields."""
    service = _build_retrieval_service(indexed_db_session)

    response = service.retrieve(query="security authentication policy", top_k=2)
    assert isinstance(response.model_dump(), dict)
    assert "results" in response.model_dump()

    if not response.results:
        pytest.skip("No results returned; cannot validate field-level structure")

    row = response.results[0]
    assert row.chunk_id is not None
    assert row.document_id is not None
    assert isinstance(row.chunk_text, str)
    assert isinstance(row.score, float)

    stored_embedding_count = indexed_db_session.scalar(select(func.count(ChunkEmbedding.id)))
    assert stored_embedding_count is not None
    assert stored_embedding_count >= 1
