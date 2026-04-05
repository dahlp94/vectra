#!/usr/bin/env python3
"""
Ingest files under data/sample_docs into Postgres (documents + chunks only).

Run from repository root:
    python scripts/ingest_sample_docs.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.session import session_scope
from app.ingestion.pipeline import ingest_folder

SAMPLE_DOCS = ROOT / "data" / "sample_docs"

DEFAULT_CHUNK_SIZE = 1000
DEFAULT_OVERLAP = 200


def main() -> None:
    configure_logging()
    get_settings()
    if not SAMPLE_DOCS.is_dir():
        raise SystemExit(f"Sample docs folder not found: {SAMPLE_DOCS}")

    with session_scope() as session:
        documents_ingested, chunks_created = ingest_folder(
            session,
            SAMPLE_DOCS,
            DEFAULT_CHUNK_SIZE,
            DEFAULT_OVERLAP,
        )

    print(
        f"Done: ingested {documents_ingested} document(s), "
        f"{chunks_created} chunk(s) from {SAMPLE_DOCS.relative_to(ROOT)}."
    )


if __name__ == "__main__":
    main()
