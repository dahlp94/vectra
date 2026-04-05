"""Document listing and detail API."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.schemas.document import DocumentDetailResponse, DocumentListResponse
from app.services.document_service import get_document_detail, list_documents

router = APIRouter(prefix="/documents", tags=["documents"])

SessionDep = Annotated[Session, Depends(get_session)]


@router.get("", response_model=DocumentListResponse)
def list_documents_route(session: SessionDep) -> DocumentListResponse:
    """Return all stored documents (metadata only; no chunk text in list)."""
    return list_documents(session)


@router.get("/{document_id}", response_model=DocumentDetailResponse)
def get_document_route(
    document_id: UUID,
    session: SessionDep,
) -> DocumentDetailResponse:
    """Return one document and its chunks."""
    detail = get_document_detail(session, document_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return detail
