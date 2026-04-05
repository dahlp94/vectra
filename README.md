# Vectra

Enterprise AI knowledge platform: ingestion, storage, and APIs toward RAG, vector search, and graph-based context.

## Overview

Vectra is a **FastAPI + PostgreSQL (pgvector)** backend that ingests documents, chunks text, stores metadata, and exposes REST APIs. **Embeddings, semantic search, RAG, and a knowledge graph are planned**, not built yet. The current milestone is a clean **ingestion and persistence** foundation.

## Problem

Enterprise knowledge lives in scattered files and systems. This project models **ingest → chunk → store → query metadata** with traceable sources, so later retrieval and generation can attach to one data model instead of ad hoc scripts.

## What works now (MVP)

- Ingestion: recursive load, `.md` / `.txt` parsing, fixed-size chunking with overlap, metadata (`doc_type`, `title`, `source_path`)
- Storage: SQLAlchemy models for documents and chunks; pgvector extension enabled in Docker for future vectors
- API surface: `/health`, `POST /ingest/folder`, `GET /documents`, `GET /documents/{id}` (ensure routers are registered in `create_app` if anything 404s)
- CLI: `scripts/ingest_sample_docs.py`; optional `scripts/seed_sample_docs.py`
- Sample corpus under `data/sample_docs/` (architecture, runbooks, incidents, policies)
- Tests: `pytest` (chunking + ingestion)

## Architecture (short)

| Layer | Responsibility |
|-------|----------------|
| Ingestion | Load → parse → chunk → metadata → DB writes |
| Storage | Postgres + SQLAlchemy; schema via `scripts/create_tables.py` |
| API | Routes → services; thin HTTP over DB reads and ingestion |

## Repo layout

- `app/api/` — FastAPI app and routes  
- `app/ingestion/` — pipeline, parser, chunker, metadata  
- `app/db/` — models, session, table creation  
- `app/schemas/`, `app/services/` — request/response models and read logic  
- `scripts/` — create tables, seed sample files, CLI ingest  
- `sql/` — Docker init (e.g. `vector`)  
- `data/sample_docs/` — demo corpus  
- `tests/` — pytest  

## Quick start

**Deps:** Python 3.11+, Docker  

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Set DATABASE_URL; default compose maps host port 5433 → container 5432
docker compose up -d
python scripts/create_tables.py
uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000