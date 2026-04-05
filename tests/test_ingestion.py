"""Tests for loading, parsing, and persisting sample documents (no embeddings)."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.db.models import Chunk, Document
from app.ingestion.loader import iter_supported_files
from app.ingestion.parser import parse_file
from app.ingestion.pipeline import ingest_folder

REPO_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DOCS = REPO_ROOT / "data" / "sample_docs"


@pytest.fixture
def db_session():
    """
    Open a DB session and ensure tables exist; tear down ingested rows afterward.

    Skips if Postgres is not configured or unreachable (minimal integration guard).
    """
    try:
        from sqlalchemy import delete

        from app.core.config import get_settings
        from app.db.init_db import create_tables
        from app.db.session import get_session_factory
    except Exception as exc:  # pragma: no cover - import/env issues
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


def test_sample_folder_loads_supported_files() -> None:
    if not SAMPLE_DOCS.is_dir():
        pytest.skip("data/sample_docs not present")
    paths = iter_supported_files(SAMPLE_DOCS)
    assert paths, "expected at least one .md or .txt file"
    assert all(p.suffix.lower() in {".md", ".txt"} for p in paths)


def test_sample_file_parses_to_text() -> None:
    if not SAMPLE_DOCS.is_dir():
        pytest.skip("data/sample_docs not present")
    first = iter_supported_files(SAMPLE_DOCS)[0]
    body = parse_file(first)
    assert isinstance(body, str)
    assert len(body.strip()) > 0


def test_ingest_folder_writes_documents_and_chunks(db_session) -> None:
    if not SAMPLE_DOCS.is_dir():
        pytest.skip("data/sample_docs not present")

    chunk_size = 800
    overlap = 100

    doc_count, chunk_count = ingest_folder(
        db_session,
        SAMPLE_DOCS,
        chunk_size=chunk_size,
        overlap=overlap,
    )
    db_session.commit()

    assert doc_count >= 1
    assert chunk_count >= 1

    stored_docs = db_session.scalars(select(Document)).all()
    stored_chunks = db_session.scalars(select(Chunk)).all()

    assert len(stored_docs) == doc_count
    assert len(stored_chunks) == chunk_count

    doc_ids = {d.id for d in stored_docs}
    for ch in stored_chunks:
        assert ch.document_id in doc_ids
        assert ch.text  # MVP: non-empty chunk bodies for sample content
        assert ch.chunk_index >= 0

    assert db_session.scalar(select(func.count()).select_from(Document)) == doc_count
    assert db_session.scalar(select(func.count()).select_from(Chunk)) == chunk_count
