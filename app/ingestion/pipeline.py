"""Orchestrate folder ingestion: load, parse, chunk, and persist documents and chunks."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Chunk, Document
from app.ingestion.chunker import chunk_text
from app.ingestion.loader import iter_supported_files
from app.ingestion.metadata import extract_metadata
from app.ingestion.parser import parse_file


def _truncate(value: str | None, max_len: int) -> str | None:
    """Trim string fields to fit ORM column limits."""
    if value is None:
        return None
    if len(value) <= max_len:
        return value
    return value[:max_len]


def ingest_folder(
    session: Session,
    folder_path: Path,
    chunk_size: int,
    overlap: int,
) -> tuple[int, int]:
    """
    Ingest all supported files under ``folder_path`` into ``Document`` and ``Chunk`` rows.

    Steps: discover files, parse text, extract path metadata, chunk text, then persist.
    Does not create embeddings.

    If a row already exists for the same ``source_path``, it is deleted first (cascades
    chunks) so re-ingestion replaces the document.

    Args:
        session: Open SQLAlchemy session (caller owns commit/rollback).
        folder_path: Root directory to scan (resolved on disk).
        chunk_size: Maximum characters per chunk.
        overlap: Overlap between consecutive chunks.

    Returns:
        ``(documents_ingested, chunks_created)`` for this run.

    Raises:
        NotADirectoryError: If ``folder_path`` is not a directory.
    """
    root = folder_path.resolve()
    if not root.is_dir():
        raise NotADirectoryError(f"Not a directory: {folder_path}")

    documents_ingested = 0
    chunks_created = 0

    for file_path in iter_supported_files(root):
        meta = extract_metadata(file_path, source_root=root)
        source_path = meta["source_path"]
        if not source_path:
            continue

        existing = session.execute(
            select(Document).where(Document.source_path == source_path)
        ).scalar_one_or_none()
        if existing is not None:
            session.delete(existing)
            session.flush()

        text = parse_file(file_path)
        title = _truncate(meta["title"], 512) or "Untitled"

        document = Document(
            title=title,
            source_path=_truncate(source_path, 2048) or "",
            doc_type=_truncate(meta["doc_type"], 128),
            team=_truncate(meta["team"], 128),
        )
        session.add(document)
        session.flush()

        for chunk_index, chunk_text_value in chunk_text(text, chunk_size, overlap):
            session.add(
                Chunk(
                    document_id=document.id,
                    chunk_index=chunk_index,
                    text=chunk_text_value,
                    metadata_json=None,
                )
            )
            chunks_created += 1

        documents_ingested += 1

    return documents_ingested, chunks_created
