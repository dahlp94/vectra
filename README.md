# Vectra

Vectra is a retrieval-augmented generation (RAG) backend for searching internal Markdown and text documents. It converts files into embeddings, stores them in PostgreSQL with pgvector, retrieves relevant passages with optional metadata filters, and generates grounded answers through a FastAPI service.

The project focuses on the core RAG workflow: reliable ingestion, vector retrieval, transparent source context, and clear API boundaries. It runs locally or with Docker Compose.

## What Vectra does

- Recursively loads `.md` and `.txt` files from a folder.
- Splits documents into deterministic, overlapping chunks.
- Generates embeddings with OpenAI `text-embedding-3-small`.
- Stores documents, chunks, metadata, and vectors in PostgreSQL with pgvector.
- Replaces previously stored content when the same `source_path` is ingested again.
- Retrieves the most relevant chunks with cosine similarity.
- Filters retrieval by `doc_type`, `team`, or `source_path`.
- Uses retrieved text to generate grounded answers with a configurable OpenAI chat model.
- Returns the answer together with supporting chunk IDs, document IDs, snippets, and relevance scores.
- Avoids calling the language model when retrieval is empty or below the relevance threshold.

## System workflow

```mermaid
flowchart TD
    A[Markdown and text files] --> B[Parse and chunk]
    B --> C[Generate embeddings]
    C --> D[(PostgreSQL + pgvector)]
    E[User question] --> F[Metadata-filtered vector search]
    D --> F
    F --> G{Relevant context found?}
    G -->|Yes| H[Grounded answer with sources]
    G -->|No| I[Fallback response]
```

The query path has four steps:

1. **Embed the question** using the same embedding configuration as the indexed chunks.
2. **Retrieve context** through pgvector similarity search and optional metadata filters.
3. **Check relevance** against the configured threshold.
4. **Generate or abstain** by either sending retrieved context to the language model or returning a fallback response.

## Implemented capabilities

| Area | Implementation |
| --- | --- |
| Ingestion | Recursive file discovery, Markdown/text parsing, deterministic chunking, overlap, and metadata extraction |
| Embeddings | Shared provider interface with batched OpenAI embeddings at ingestion and query time |
| Storage | Relational document and chunk records plus pgvector embeddings in PostgreSQL |
| Re-ingestion | Existing records are replaced when a matching `source_path` is ingested again |
| Retrieval | Ranked cosine-similarity search with configurable `top_k` and exact metadata filters |
| RAG | Context-grounded generation with a relevance gate and fallback behavior |
| Traceability | Supporting chunk and document identifiers, snippets, and retrieval scores returned with answers |
| API | Health, folder ingestion, document listing, document detail, and RAG query endpoints |
| Testing | Coverage for chunking, ingestion, retrieval filters, health checks, and query behavior |

## Example request

After starting the API and ingesting the sample documents:

```bash
curl -s -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the deployment approval process?",
    "top_k": 5,
    "filters": {
      "doc_type": "policies"
    }
  }'
```

The response contains:

- `answer`: a grounded response or a fallback when the available context is insufficient.
- `citations`: the chunk and document identifiers, text snippets, and scores supporting the answer.
- `retrieved_chunks`: the ranked context supplied to the generation step.

Exact content depends on the indexed documents and configured models.

## API endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Check API availability |
| `POST` | `/ingest/folder` | Parse, chunk, embed, and store supported files from a folder |
| `GET` | `/documents` | List stored documents and metadata |
| `GET` | `/documents/{document_id}` | Return one document and its chunks |
| `POST` | `/query` | Retrieve relevant context and return a grounded answer |

## Technology

- **Language:** Python 3.11+
- **API:** FastAPI, Uvicorn, Pydantic
- **Data layer:** PostgreSQL, pgvector, SQLAlchemy 2
- **Embeddings:** OpenAI `text-embedding-3-small` by default
- **Generation:** OpenAI Chat Completions with a configurable model; `gpt-4o-mini` by default
- **Environment:** Docker Compose and `.env` configuration
- **Testing:** pytest

## Repository structure

```text
vectra/
├── app/
│   ├── api/                 # FastAPI app and routes
│   ├── core/                # Settings and logging
│   ├── db/                  # SQLAlchemy models and sessions
│   ├── embeddings/          # Embedding provider and service
│   ├── ingestion/           # Loading, parsing, chunking, and persistence
│   ├── rag/                 # Prompt construction and RAG orchestration
│   ├── retrieval/           # Filters, vector search, and retrieval service
│   ├── schemas/             # Request and response models
│   └── services/            # Document read operations
├── data/sample_docs/        # Example corpus
├── scripts/                 # Database, ingestion, and sample-data utilities
├── sql/                     # pgvector initialization
├── tests/                   # Automated tests
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md
```

## Local setup

### 1. Create the environment

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

On Windows, activate the environment with:

```powershell
.venv\Scripts\activate
```

If `openai` is not yet included in `requirements.txt`, install it separately:

```bash
pip install openai
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Set `OPENAI_API_KEY` and confirm that `DATABASE_URL` uses the same host port exposed by Docker Compose.

The default Compose configuration publishes PostgreSQL on port `5433`:

```env
DATABASE_URL=postgresql+psycopg2://vectra:vectra@localhost:5433/vectra
OPENAI_API_KEY=your_api_key
```

Other configurable values include `EMBEDDING_MODEL`, `EMBEDDING_DIMENSION`, `OPENAI_CHAT_MODEL`, `LOG_LEVEL`, and `APP_ENV`.

### 3. Start PostgreSQL and create the tables

```bash
docker compose up -d
docker compose ps
python scripts/create_tables.py
```

Wait until PostgreSQL is healthy before creating the tables.

### 4. Ingest the sample corpus

The repository includes example documents in `data/sample_docs/`.

```bash
python scripts/ingest_sample_docs.py
```

This step calls the embedding API and requires a valid `OPENAI_API_KEY`.

### 5. Run the API

```bash
uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000/docs` for the interactive API documentation.

## Additional examples

### Health check

```bash
curl -s http://localhost:8000/health
```

```json
{"status":"ok"}
```

### Ingest a folder through the API

```bash
curl -s -X POST http://localhost:8000/ingest/folder \
  -H "Content-Type: application/json" \
  -d '{
    "folder_path": "./data/sample_docs",
    "chunk_size": 1000,
    "overlap": 200
  }'
```

### Inspect stored documents

```bash
curl -s http://localhost:8000/documents
curl -s http://localhost:8000/documents/<document_id>
```

## Testing

Run the test suite with:

```bash
pytest
```

The tests cover deterministic chunking, ingestion behavior, metadata-filtered retrieval, API health, and grounded-query behavior. Database-dependent tests require an available PostgreSQL instance with pgvector.

## Design decisions

- **Shared embedding configuration:** indexed chunks and user questions use the same model and vector dimension.
- **Explicit persistence model:** documents, chunks, and embeddings remain separate, inspectable records.
- **Thin API routes:** application logic is delegated to ingestion, retrieval, document, and RAG services.
- **Retrieval before generation:** the language model receives only selected document context.
- **Relevance-aware fallback:** weak retrieval does not trigger an unsupported generated answer.
- **Visible source context:** API consumers can inspect the passages and scores used for each response.

## Current scope

Vectra is a working local and Docker-based RAG backend. The current version uses dense vector retrieval and exact metadata filters.

The following capabilities are not part of the current implementation:

- Knowledge graphs or GraphRAG
- Hybrid keyword and vector retrieval
- Reranking
- Authentication or multi-tenant permissions
- Background ingestion workers
- Production monitoring and distributed tracing
- Cloud deployment
- A user interface

The next practical milestone is a reproducible end-to-end evaluation covering retrieval relevance, answer grounding, and failure cases.
