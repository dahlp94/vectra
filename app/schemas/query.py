"""Pydantic schemas for retrieval query requests and responses."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """Incoming retrieval query payload."""

    query: str = Field(..., min_length=1)
    top_k: int | None = Field(default=None, ge=1)
    filters: dict[str, Any] | None = None


class QueryResult(BaseModel):
    """Single retrieval result."""

    chunk_id: UUID
    document_id: UUID
    chunk_text: str
    score: float


class QueryResponse(BaseModel):
    """Retrieval response containing ranked chunk results."""

    results: list[QueryResult] = Field(default_factory=list)
