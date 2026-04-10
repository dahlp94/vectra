# Vectra

Enterprise AI knowledge platform: ingestion, vector indexing, and **semantic retrieval** over Postgres/pgvector, structured toward RAG, graph-based context, and production operations.

## Overview

Vectra is a **production-style** backend for turning enterprise documents into **searchable, metadata-aware vector indexes**. The stack ingests files, chunks text, embeds chunks with a pluggable provider (OpenAI in the MVP), persists vectors in **PostgreSQL with pgvector**, and runs **query-time semantic retrieval** with optional filters on document metadata.

The product direction is **retrieval-augmented generation (RAG)**, **semantic / hybrid search**, and **graph-based context** for grounded answers. **Semantic retrieval is implemented today**: query embedding, cosine similarity over chunk embeddings, metadata filtering, and ranked results. LLM answer generation and graph layers are **not** implemented yet.

## Why This Project

Enterprise knowledge is fragmented across wikis, runbooks, tickets, and policy folders. Keyword search misses paraphrases and cross-domain phrasing; teams need **semantic matching** plus **structured filters** (document type, owning team, source path) so answers can be constrained to the right corpus. That is an **AI infrastructure** problem: consistent chunking, a single embedding space, durable storage, and a retrieval contract that downstream RAG or agents can trust.

## Current Capabilities (MVP)

### Ingestion

- Recursive loading of supported files (Markdown and plain text)
- Parsing, deterministic chunking with overlap
- Metadata extraction: `doc_type`, `title`, `source_path`, `team`
- Persistence of documents and chunks

### Embedding and indexing

- Embedding **provider abstraction** with an **OpenAI** implementation (`text-embedding-3-small` by default)
- Batched embedding service for chunk text
- Storage of **chunk-level embeddings** in pgvector-backed columns, aligned with configured embedding dimension

### Retrieval

- Query embedding in the **same embedding space** as indexed chunks
- **pgvector similarity search** (cosine distance) over stored embeddings
- **Metadata-aware filtering** on `doc_type`, `team`, and `source_path` (via document joins)
- **Retrieval orchestration** returning ranked chunk text, IDs, and similarity-derived scores

### Platform

- FastAPI application with modular routes (`health`, `ingest`, `documents`)
- Service layers for documents and retrieval (`RetrievalService`)
- CLI script to ingest the bundled sample corpus with embeddings
- Sample enterprise documents: architecture, runbooks, incidents, policies
- Pytest coverage for chunking, ingestion, and retrieval (including filter behavior)

## Architecture Overview

| Layer | Responsibility |
|-------|----------------|
| **Ingestion** | Discover files, parse, chunk, extract metadata, write documents and chunks; invoke embedding service and persist **ChunkEmbedding** rows. |
| **Embedding** | Provider abstraction and batched calls; shared settings for model and dimension. |
| **Storage** | PostgreSQL; relational tables for documents and chunks; **pgvector** for dense vectors; JSON metadata on chunks where applicable. |
| **Retrieval** | Embed the user query, run **similarity search** over chunk embeddings, apply **SQL filters** on document metadata, return **top-k ranked** results with scores. |
| **API** | HTTP surface for health, folder ingestion, and document listing/detail; retrieval is available through **`RetrievalService`** (add a dedicated route when you expose search over HTTP). |

## Retrieval Flow

1. **Query embedding** — The user query string is embedded with the same provider/model family used at ingest time so vectors are comparable.
2. **Vector similarity search** — pgvector computes distance against stored chunk embeddings; results are ordered by relevance (cosine distance in the implementation layer; scores exposed as similarity-style values).
3. **Metadata filtering** — Optional filters restrict candidates to documents matching `doc_type`, `team`, and/or `source_path` before ranking.
4. **Ranked results** — The service returns up to **top_k** chunks with `chunk_id`, `document_id`, `chunk_text`, and `score`, suitable for downstream RAG context assembly.

## Repository Structure

| Path | Purpose |
|------|---------|
| `app/api/` | FastAPI app factory and route modules (`health`, `ingest`, `documents`). |
| `app/ingestion/` | Loader, parser, chunker, metadata, ingestion pipeline (including embedding writes). |
| `app/embeddings/` | Provider abstraction, OpenAI implementation, embedding service. |
| `app/retrieval/` | Filters, pgvector-backed similarity search, `RetrievalService` orchestration. |
| `app/services/` | Document read logic. |
| `app/db/` | SQLAlchemy models (documents, chunks, embeddings), session, schema creation. |
| `app/schemas/` | Pydantic models for APIs and retrieval (`QueryRequest`, `QueryResponse`, etc.). |
| `data/sample_docs/` | Sample enterprise corpus for local demos and tests. |
| `scripts/` | Table creation, CLI ingestion. |
| `sql/` | Docker init for the `vector` extension. |
| `tests/` | Pytest: chunking, ingestion, retrieval. |

## Getting Started

**Prerequisites:** Python 3.11+, Docker, an **OpenAI API key** for embeddings (or adapt the provider layer for another backend).

### Environment

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install openai          # required by OpenAIEmbeddingProvider (runtime dependency)
cp .env.example .env
```

Set **`OPENAI_API_KEY`** and **`DATABASE_URL`** in `.env`. The bundled `docker-compose.yml` maps Postgres to host port **5433** by default; align `DATABASE_URL` (example: `postgresql+psycopg2://vectra:vectra@localhost:5433/vectra`).

### Database

```bash
docker compose up -d
python scripts/create_tables.py
```

### API

```bash
uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000
```

Register ingest and document routers in `create_app` if they are not already included, so `/ingest/folder` and `/documents` are reachable.

### Ingest sample documents (with embeddings)

```bash
python scripts/ingest_sample_docs.py
```

Requires a valid `OPENAI_API_KEY` and network access to the OpenAI embeddings API.

## Example Workflow

1. **Seed** sample files (optional): `python scripts/seed_sample_docs.py` if you need to regenerate `data/sample_docs/`.
2. **Create tables** and **start Postgres** (see above).
3. **Ingest** with embeddings: `python scripts/ingest_sample_docs.py` (or `POST /ingest/folder` with a folder path and chunk settings).
4. **Inspect** data via `GET /documents` and `GET /documents/{id}`.
5. **Retrieve** semantically using Python (see below) or add an HTTP route that calls `RetrievalService.retrieve`.

## Example Query

**Input**

- Natural-language query: `deployment approvals`
- Optional filters: `{"doc_type": "policies"}`

**Programmatic retrieval**

```python
from app.db.session import session_scope
from app.retrieval.service import RetrievalService

with session_scope() as session:
    service = RetrievalService(session=session)
    response = service.retrieve(
        query="deployment approvals",
        top_k=5,
        filters={"doc_type": "policies"},
    )
    for result in response.results:
        print(result.score, result.chunk_text[:200])
```

**Illustrative output (shortened)**

Scores and text depend on your corpus and model; structurally you get ranked rows such as:

- `0.82` — excerpt referencing change classes, approval gates, and deployment policy windows…
- `0.79` — excerpt tying API Gateway authentication policy to deployment policy references…

Each result includes `chunk_id`, `document_id`, full `chunk_text`, and `score` for downstream RAG or UI use.

## Roadmap

| Horizon | Focus |
|---------|--------|
| **Week 5** | **RAG answer generation**: LLM calls, citation-style grounding on retrieved chunks, prompt orchestration. |
| **Week 6+** | **Graph-based context**: entities, relationships, cross-document links feeding retrieval or prompts. |
| **Platform** | Authentication and authorization; **evaluation** (retrieval quality, answer faithfulness); **monitoring and observability**; **caching** and latency optimizations. |

## Design Principles

- **Modular architecture** — Ingestion, embeddings, retrieval, and HTTP layers are separated behind clear interfaces.
- **Separation of concerns** — Routes delegate to services; vector logic lives in retrieval modules, not in parsers.
- **Retrieval-first** — Storage and embeddings are shaped for **semantic search** and filterable ranked results, not ad hoc scripts.
- **Extensibility** — Embedding providers are pluggable behind a small ABC; filters can be extended while keeping SQL composition explicit.
- **Production-style patterns** — Central settings, explicit sessions, typed schemas, and automated tests for critical paths.

## Summary

- Designed and implemented an **end-to-end enterprise ingestion and vector retrieval stack** using **FastAPI**, **SQLAlchemy**, **PostgreSQL**, and **pgvector**, with **OpenAI embeddings** and **metadata-filtered semantic search**.
- Built **retrieval infrastructure**: query embedding, **cosine similarity** retrieval, ranked results, and pytest coverage for **embedding + filtering** behavior.
- Positioned the system for **RAG and graph-augmented context** through a **provider abstraction**, service-layer orchestration, and document/chunk/embedding data model separation.
