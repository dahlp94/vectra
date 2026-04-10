"""Convert retrieval results into compact citation records for API and RAG output."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from app.schemas.query import QueryResponse, QueryResult

_DEFAULT_MAX_SNIPPET_CHARS = 280
_WHITESPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True, slots=True)
class ChunkCitation:
    """Traceable citation derived from a retrieved chunk (MVP shape)."""

    chunk_id: UUID
    document_id: UUID
    chunk_text_snippet: str
    score: float


def truncate_snippet(text: str, *, max_chars: int = _DEFAULT_MAX_SNIPPET_CHARS) -> str:
    """
    Produce a concise, API-safe snippet from full chunk text.

    Collapses internal whitespace and truncates with an ellipsis when needed.
    """
    if max_chars < 1:
        raise ValueError("max_chars must be >= 1")
    collapsed = _WHITESPACE_RE.sub(" ", text.strip())
    if len(collapsed) <= max_chars:
        return collapsed
    if max_chars <= 3:
        return collapsed[:max_chars]
    return collapsed[: max_chars - 3].rstrip() + "..."


def citation_from_query_result(
    result: QueryResult,
    *,
    max_snippet_chars: int = _DEFAULT_MAX_SNIPPET_CHARS,
) -> ChunkCitation:
    """Map a single ``QueryResult`` to a ``ChunkCitation`` with a short snippet."""
    return ChunkCitation(
        chunk_id=result.chunk_id,
        document_id=result.document_id,
        chunk_text_snippet=truncate_snippet(result.chunk_text, max_chars=max_snippet_chars),
        score=float(result.score),
    )


def citations_from_query_results(
    results: Sequence[QueryResult],
    *,
    max_snippet_chars: int = _DEFAULT_MAX_SNIPPET_CHARS,
) -> list[ChunkCitation]:
    """Convert an ordered list of retrieval results to citations (same order)."""
    return [citation_from_query_result(r, max_snippet_chars=max_snippet_chars) for r in results]


def citations_from_retrieval_response(
    response: QueryResponse,
    *,
    max_snippet_chars: int = _DEFAULT_MAX_SNIPPET_CHARS,
) -> list[ChunkCitation]:
    """Convenience wrapper for a full ``QueryResponse`` from the retrieval layer."""
    return citations_from_query_results(response.results, max_snippet_chars=max_snippet_chars)
