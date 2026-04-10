"""Week 3 groundwork tests for embedding generation and persistence."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import delete, select

from app.core.config import get_settings
from app.db.models import Chunk, ChunkEmbedding, Document
from app.embeddings.provider import EmbeddingProvider
from app.ingestion.pipeline import ingest_folder

REPO_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DOCS = REPO_ROOT / "data" / "sample_docs"


class _FakeEmbeddingProvider(EmbeddingProvider):
    """Deterministic provider for lightweight ingestion+embedding validation."""

    def __init__(self, dimension: int) -> None:
        self._dimension = dimension

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for i, _ in enumerate(texts):
            base = float(i + 1)
            vectors.append([base] * self._dimension)
        return vectors


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


def test_ingestion_generates_and_stores_chunk_embeddings(db_session, monkeypatch: pytest.MonkeyPatch) -> None:
    """Validate that ingestion writes one embedding row per stored chunk."""
    if not SAMPLE_DOCS.is_dir():
        pytest.skip("data/sample_docs not present")

    settings = get_settings()
    monkeypatch.setattr(
        "app.ingestion.pipeline._build_embedding_provider",
        lambda: _FakeEmbeddingProvider(settings.embedding_dimension),
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

    chunks = db_session.scalars(select(Chunk)).all()
    embeddings = db_session.scalars(select(ChunkEmbedding)).all()

    assert len(chunks) == chunk_count
    assert len(embeddings) == len(chunks)

    chunk_ids = {chunk.id for chunk in chunks}
    for row in embeddings:
        assert row.chunk_id in chunk_ids
        assert len(row.embedding) == settings.embedding_dimension
        assert row.embedding_model == settings.embedding_model
