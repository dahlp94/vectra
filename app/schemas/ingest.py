"""Pydantic schemas for ingestion endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class IngestFolderRequest(BaseModel):
    """Request payload for folder-based document ingestion."""

    folder_path: str = Field(..., description="Absolute or relative folder path to ingest.")
    chunk_size: int = Field(default=1000, gt=0, description="Maximum characters per chunk.")
    overlap: int = Field(default=200, ge=0, description="Character overlap between adjacent chunks.")

    @model_validator(mode="after")
    def validate_overlap(self) -> "IngestFolderRequest":
        """Ensure overlap remains smaller than chunk size."""
        if self.overlap >= self.chunk_size:
            raise ValueError("overlap must be smaller than chunk_size")
        return self


class IngestFolderResponse(BaseModel):
    """Result summary returned after folder ingestion completes."""

    documents_ingested: int = Field(..., ge=0)
    chunks_created: int = Field(..., ge=0)
