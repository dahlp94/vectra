"""Pydantic schemas for retrieval queries and RAG answer responses."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """Incoming query payload (retrieval and RAG)."""

    query: str = Field(..., min_length=1)
    top_k: int | None = Field(default=None, ge=1)
    filters: dict[str, Any] | None = None


class QueryResult(BaseModel):
    """Single vector retrieval result (full chunk text and score)."""

    chunk_id: UUID
    document_id: UUID
    chunk_text: str
    score: float


class QueryResponse(BaseModel):
    """Retrieval response containing ranked chunk results."""

    results: list[QueryResult] = Field(default_factory=list)


class RetrievedChunkSummary(BaseModel):
    """Compact view of a retrieved chunk for the client (snippet + ids + score)."""

    chunk_id: UUID
    document_id: UUID
    chunk_text_snippet: str
    score: float


class Citation(BaseModel):
    """Traceable source reference for an answer."""

    chunk_id: UUID
    document_id: UUID
    chunk_text_snippet: str
    score: float


class RagQueryResponse(BaseModel):
    """Grounded RAG answer with citations and retrieved chunk summaries."""

    answer: str
    citations: list[Citation] = Field(default_factory=list)
    retrieved_chunks: list[RetrievedChunkSummary] = Field(default_factory=list)
