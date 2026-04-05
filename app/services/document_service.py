"""Read-side operations for documents exposed to the API."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import Document
from app.schemas.document import (
    DocumentDetailResponse,
    DocumentListItemResponse,
    DocumentListResponse,
)


def list_documents(session: Session) -> DocumentListResponse:
    """
    List all documents, newest first.

    Does not load chunk bodies (list payload stays small).
    """
    rows = session.execute(
        select(Document).order_by(Document.created_at.desc())
    ).scalars().all()
    return DocumentListResponse(
        documents=[DocumentListItemResponse.model_validate(d) for d in rows],
    )


def get_document_detail(session: Session, document_id: UUID) -> DocumentDetailResponse | None:
    """
    Load one document with its chunks ordered by ``chunk_index``.

    Returns ``None`` if no document exists for ``document_id``.
    """
    document = session.execute(
        select(Document)
        .where(Document.id == document_id)
        .options(selectinload(Document.chunks))
    ).scalar_one_or_none()
    if document is None:
        return None
    return DocumentDetailResponse.model_validate(document)
