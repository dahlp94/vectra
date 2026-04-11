# Vectra

**Vectra** is a production-style **AI knowledge platform** MVP: it ingests enterprise-style documents from disk, indexes them with **dense embeddings** in **PostgreSQL + pgvector**, runs **metadata-aware semantic retrieval**, and answers questions with a **grounded RAG** layer that returns **citations** and **retrieved chunk summaries**.

The codebase is structured for clarity and extension. It is intended to run **locally or via Docker Compose** for demos and portfolio review; it is not a full managed SaaS deployment.

The product direction includes **graph-based context** and deeper platform concerns; those are **not** implemented in the current MVP.


## Why this project

Enterprise knowledge lives in runbooks, policies, tickets, and architecture notes. Keyword search often misses paraphrases and cross-references. Teams need **semantic retrieval** over a consistent chunking and embedding pipeline, optional **filters** on document metadata (type, team, path), and **answers grounded in retrieved text** so responses are traceable—not generic chatbot speculation.

Vectra addresses that **AI infrastructure** problem: durable storage, a single embedding space, explicit retrieval, and an API contract that exposes **what** was used to answer.


## Core features (MVP)

| Area | What is implemented |
|------|---------------------|
| **Ingestion** | Recursive load of `.md` / `.txt`, parsing, deterministic chunking with overlap, metadata extraction (`doc_type`, `title`, `source_path`, `team`). |
| **Embeddings** | Pluggable provider abstraction; **OpenAI** embeddings (`text-embedding-3-small` by default) batched at ingest and query time. |
| **Storage** | PostgreSQL with **pgvector** for chunk vectors; relational documents and chunks. Re-ingesting the same `source_path` replaces prior rows. |
| **Retrieval** | Query embedding, cosine-style similarity search, optional **metadata filters** (`doc_type`, `team`, `source_path`), ranked results with scores. |
| **RAG** | Grounded prompts from retrieved chunks, **OpenAI Chat Completions** for answers (configurable model), **citations** and **retrieved chunk snippets** in API responses; safe fallback when context is missing or below relevance threshold. |
| **API** | FastAPI: health, folder ingestion, document listing/detail, RAG query. |


## Architecture

Data and control flow are layered so each stage has a clear responsibility.

```text
┌─────────────────────────────────────────────────────────────────┐
│                         HTTP API (FastAPI)                       │
│   /health  /ingest/folder  /documents  /documents/{id}  /query │
└───────────────────────────────┬─────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        ▼                       ▼                       ▼
┌───────────────┐     ┌─────────────────┐     ┌───────────────────┐
│   Ingestion   │     │    Retrieval    │     │   RAG orchestration│
│   pipeline    │     │    service      │     │   (prompt + LLM)   │
└───────┬───────┘     └────────┬────────┘     └─────────┬─────────┘
        │                      │                        │
        ▼                      ▼                        │
┌───────────────┐     ┌─────────────────┐              │
│  Embeddings   │     │  Vector store   │◄─────────────┘
│  service      │     │  (pgvector SQL)  │
└───────┬───────┘     └────────┬────────┘
        │                    │
        └──────────┬─────────┘
                   ▼
        ┌──────────────────────┐
        │  Storage (Postgres)  │
        │  documents, chunks,  │
        │  chunk_embeddings    │
        └──────────────────────┘
```

**Layers in brief**

- **Ingestion** — Discover files, parse, chunk, extract metadata, persist documents and chunks, then **embed chunks** and persist **ChunkEmbedding** rows.
- **Embeddings** — Shared provider settings (model, dimension); used at ingest and at query time for the user question.
- **Storage** — SQLAlchemy models and sessions; pgvector columns for vectors.
- **Retrieval** — Embed the query, run similarity search with optional document metadata filters, return ranked `QueryResult` rows.
- **RAG orchestration** — Build context from retrieved chunks, call the LLM with a grounded system/user style prompt, map results to **citations** and **retrieved chunk summaries**.
- **API** — Thin routes delegating to services; Pydantic request/response models.


## RAG pipeline (query path)

1. **Embed the question** — Same embedding model family as chunks so vectors are comparable.
2. **Retrieve** — pgvector similarity search over `chunk_embeddings`, joined to documents for metadata; optional filters narrow the corpus.
3. **Gate** — If there are no hits or the best score is below an internal threshold, the API returns a short **fallback** answer with **empty** citations and retrieved chunks (no LLM call).
4. **Generate** — Otherwise, assemble context from chunk text, build a grounded prompt, call **OpenAI Chat Completions**, return **answer**, **citations**, and **retrieved_chunks** (snippets and scores).


## Repository structure

```text
vectra/
├── app/
│   ├── api/                 # FastAPI app factory, routes (health, ingest, documents, query)
│   ├── core/                # Settings, logging
│   ├── db/                  # SQLAlchemy models, session, DB helpers
│   ├── embeddings/          # Provider + embedding service
│   ├── ingestion/           # Loader, parser, chunker, metadata, pipeline
│   ├── rag/                 # Prompting, citations, RAG service
│   ├── retrieval/           # Filters, vector store, retrieval service
│   ├── schemas/             # Pydantic models for APIs and query/RAG
│   └── services/            # Document read logic
├── data/sample_docs/        # Sample corpus (architecture, runbooks, incidents, policies)
├── scripts/                 # create_tables, ingest_sample_docs, seed_sample_docs
├── sql/                     # pgvector extension init for Docker
├── tests/                   # pytest (chunking, health, ingestion, retrieval, query API)
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md
```


## Prerequisites

- **Python** 3.11+
- **Docker** (for Postgres + pgvector)
- **OpenAI API key** — used for embeddings and for RAG chat completions in the default configuration


## Setup

### 1. Virtual environment and dependencies

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install openai            # Required for OpenAI embeddings and RAG (not pinned in requirements.txt)
```

### 2. Environment variables

```bash
cp .env.example .env
```

Edit `.env`:

- Set **`OPENAI_API_KEY`**.
- Set **`DATABASE_URL`** to match how you run Postgres.

`docker-compose.yml` publishes Postgres on host port **`5433`** by default (`${POSTGRES_PORT:-5433}:5432`). Example URL:

```bash
DATABASE_URL=postgresql+psycopg2://vectra:vectra@localhost:5433/vectra
```

The bundled `.env.example` uses port `5432`; **align the port with Compose** if you use the default Compose mapping.

Other useful settings: `EMBEDDING_MODEL`, `EMBEDDING_DIMENSION`, `LOG_LEVEL`, `APP_ENV`. Optional: **`OPENAI_CHAT_MODEL`** for RAG (defaults to `gpt-4o-mini` in code if unset).

### 3. Database

```bash
docker compose up -d
python scripts/create_tables.py
```

Wait until the Postgres service is healthy (`docker compose ps`).

### 4. Run the API

```bash
uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000
```

Interactive docs: `http://localhost:8000/docs`


## Demo flow (end-to-end)

1. **Optional — regenerate sample files** (the repo already includes `data/sample_docs/`):

   ```bash
   python scripts/seed_sample_docs.py
   ```

2. **Ingest the sample corpus** (chunks + embeddings; requires network access to OpenAI):

   ```bash
   python scripts/ingest_sample_docs.py
   ```

   Alternatively, ingest any folder of `.md`/`.txt` files via **`POST /ingest/folder`** (see below).

3. **Query** with **`POST /query`** after the API is running.

### Example: health check

```bash
curl -s http://localhost:8000/health
```

Example response:

```json
{"status":"ok"}
```

### Example: RAG query

```bash
curl -s -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the deployment approval process?",
    "top_k": 5,
    "filters": {"doc_type": "policies"}
  }'
```

**Typical response shape** (`RagQueryResponse`):

- **`answer`** — string (grounded answer, or a short fallback if retrieval is insufficient).
- **`citations`** — list of `{ chunk_id, document_id, chunk_text_snippet, score }`.
- **`retrieved_chunks`** — list of `{ chunk_id, document_id, chunk_text_snippet, score }` (aligned with what supported the answer when the LLM path runs).

Exact text depends on your corpus and models.

### Example: ingest a folder via API

```bash
curl -s -X POST http://localhost:8000/ingest/folder \
  -H "Content-Type: application/json" \
  -d '{
    "folder_path": "./data/sample_docs",
    "chunk_size": 1000,
    "overlap": 200
  }'
```

Example response:

```json
{"documents_ingested":4,"chunks_created":<n>}
```

Folder ingestion **parses chunks, generates embeddings, and persists vectors** (requires `OPENAI_API_KEY`).

### Example: list documents

```bash
curl -s http://localhost:8000/documents
```

### Example: document detail

Replace `<uuid>` with a real `document_id` from the list response:

```bash
curl -s http://localhost:8000/documents/<uuid>
```


## API summary

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Liveness; returns `{ "status": "ok" }`. |
| `POST` | `/ingest/folder` | Body: `folder_path`, `chunk_size`, `overlap`. Ingests supported files, creates chunks, **embeds and stores vectors**. Response: `documents_ingested`, `chunks_created`. |
| `GET` | `/documents` | Lists stored documents (metadata; not full chunk text in the list). |
| `GET` | `/documents/{document_id}` | Document detail including chunks. `404` if missing. |
| `POST` | `/query` | Body: `query` (required), optional `top_k`, optional `filters` (e.g. `doc_type`, `team`, `source_path`). Returns grounded **`answer`**, **`citations`**, **`retrieved_chunks`**. Client errors `400`; upstream LLM failures `502` where applicable. |


## Tech stack (MVP)

- **Language:** Python 3.11+
- **Web:** FastAPI, Uvicorn
- **Data:** PostgreSQL, **pgvector**, SQLAlchemy 2
- **Config:** Pydantic Settings, `.env`
- **Embeddings / RAG (default):** OpenAI API (`openai` Python package)


## Testing

```bash
pytest
```

Tests cover chunking, ingestion, retrieval (including filters), health, and the query API. They favor **behavior** over heavy mocking where practical.


## Future work

Plausible extensions (not in the current MVP):

- **Knowledge graph** — Entities and relationships for richer context and hybrid retrieval.
- **Auth and permissions** — Tenant-scoped or document-level access control for retrieval.
- **Background workers** — Async ingestion and re-embedding at scale.
- **Evaluation** — Retrieval metrics, answer faithfulness, regression datasets.
- **Observability** — Structured metrics, tracing, and production logging sinks.
- **Caching** — Embedding and retrieval caches for latency and cost.


## Design principles

- **Separation of concerns** — Routes stay thin; ingestion, retrieval, and RAG live in services.
- **One embedding space** — Same model settings for index and query vectors.
- **Explicit data model** — Documents, chunks, and embeddings are first-class tables.
- **Traceability** — RAG responses expose citations and retrieved snippets for inspection and demos.


## License and Status

This repository represents a **portfolio-grade MVP backend**, designed for local and containerized execution, technical evaluation, and system design discussions.

It demonstrates production-style architecture and engineering practices, but does **not** reflect a fully hardened production system. Capabilities such as multi-tenant support, comprehensive observability (monitoring, alerting, tracing), and SRE-grade operational readiness are intentionally out of scope for this stage.
