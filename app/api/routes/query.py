"""RAG query API."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.rag.service import RAGService
from app.schemas.query import QueryRequest, RagQueryResponse

router = APIRouter(tags=["query"])

SessionDep = Annotated[Session, Depends(get_session)]


@router.post("/query", response_model=RagQueryResponse)
def post_query(body: QueryRequest, session: SessionDep) -> RagQueryResponse:
    """Answer a question using retrieved context and a grounded LLM prompt."""
    service = RAGService(session)
    try:
        return service.complete_query(body.query, top_k=body.top_k, filters=body.filters)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
