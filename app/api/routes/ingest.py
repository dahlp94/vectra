"""Folder ingestion API."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.ingestion.pipeline import ingest_folder
from app.schemas.ingest import IngestFolderRequest, IngestFolderResponse

router = APIRouter(prefix="/ingest", tags=["ingest"])

SessionDep = Annotated[Session, Depends(get_session)]


@router.post("/folder", response_model=IngestFolderResponse)
def ingest_folder_route(body: IngestFolderRequest, session: SessionDep) -> IngestFolderResponse:
    """
    Scan ``folder_path`` for ``.md`` / ``.txt`` files, chunk them, and store rows.

    Embeddings are not generated in this MVP phase.
    """
    folder = Path(body.folder_path).expanduser()
    try:
        documents_ingested, chunks_created = ingest_folder(
            session,
            folder,
            body.chunk_size,
            body.overlap,
        )
    except NotADirectoryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        session.commit()
    except Exception:
        session.rollback()
        raise

    return IngestFolderResponse(
        documents_ingested=documents_ingested,
        chunks_created=chunks_created,
    )
