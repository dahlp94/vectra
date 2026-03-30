"""Pydantic schemas for document listing and detail endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ChunkResponse(BaseModel):
    """Serialized chunk for document detail responses."""

    id: UUID
    chunk_index: int = Field(..., ge=0)
    text: str
    metadata_json: dict[str, Any] | None = None

    model_config = ConfigDict(from_attributes=True)


class DocumentListItemResponse(BaseModel):
    """Serialized document item for list responses."""

    id: UUID
    title: str
    source_path: str
    doc_type: str | None = None
    team: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentListResponse(BaseModel):
    """Pageless document list response for MVP."""

    documents: list[DocumentListItemResponse]


class DocumentDetailResponse(BaseModel):
    """Serialized document details including chunk data."""

    id: UUID
    title: str
    source_path: str
    doc_type: str | None = None
    team: str | None = None
    created_at: datetime
    chunks: list[ChunkResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
