"""RAG orchestration: retrieve chunks, build prompts, call LLM, format citations."""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.rag.citations import citations_from_query_results
from app.rag.prompting import assemble_context_block, build_grounded_rag_prompt
from app.retrieval.service import RetrievalService
from app.schemas.query import Citation, QueryResponse, RagQueryResponse, RetrievedChunkSummary

MIN_SCORE_THRESHOLD = 0.22

_FALLBACK_ANSWER = "I don't know based on the provided documents."
_DEFAULT_CHAT_MODEL = "gpt-4o-mini"


def _openai_chat_completion(prompt: str, *, model: str | None = None) -> str:
    """Generate a completion using the OpenAI Chat Completions API (MVP, synchronous)."""
    settings = get_settings()
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is required for RAG answer generation.")

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError(
            "openai package is required for RAG. Install it with: pip install openai"
        ) from exc

    resolved_model = model or os.getenv("OPENAI_CHAT_MODEL", _DEFAULT_CHAT_MODEL)
    client = OpenAI(api_key=settings.openai_api_key)
    response = client.chat.completions.create(
        model=resolved_model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )
    message = response.choices[0].message
    content = message.content if message else None
    if not content:
        raise RuntimeError("OpenAI returned an empty completion.")
    return content


def _should_fallback(retrieval_response: QueryResponse) -> bool:
    """True when there are no hits or the best match is below the relevance threshold."""
    results = retrieval_response.results
    if not results:
        return True
    max_score = max(r.score for r in results)
    return max_score < MIN_SCORE_THRESHOLD


class RAGService:
    """Coordinates retrieval, prompting, generation, and citation formatting."""

    def __init__(
        self,
        session: Session | None,
        *,
        retrieval_service: Any | None = None,
        llm_complete: Callable[[str], str] | None = None,
        chat_model: str | None = None,
    ) -> None:
        """
        Args:
            session: DB session for the default ``RetrievalService`` (not required if
                ``retrieval_service`` is injected).
            retrieval_service: Optional retrieval implementation (for tests).
            llm_complete: Optional ``(prompt) -> answer`` override (for tests).
            chat_model: Optional OpenAI chat model when using the default OpenAI path.
        """
        if retrieval_service is not None:
            self._retrieval = retrieval_service
        elif session is not None:
            self._retrieval = RetrievalService(session)
        else:
            raise ValueError("session is required when retrieval_service is not provided")
        self._llm_complete = llm_complete
        self._chat_model = chat_model

    def complete_query(
        self,
        query: str,
        top_k: int | None = None,
        filters: Mapping[str, Any] | None = None,
    ) -> RagQueryResponse:
        """
        Run retrieval, then—only if chunks exist—build a grounded prompt and generate an answer.

        When retrieval yields no chunks or scores below threshold, returns a safe fallback
        and skips the LLM (no citations or chunk summaries).
        """
        retrieval_response: QueryResponse = self._retrieval.retrieve(query, top_k=top_k, filters=filters)
        scores = [r.score for r in retrieval_response.results]
        max_score = max(scores) if scores else None
        print(f"[RAG debug] retrieval_scores={scores}")
        print(f"[RAG debug] max_score={max_score}")
        print(f"[RAG debug] threshold={MIN_SCORE_THRESHOLD}")
        if _should_fallback(retrieval_response):
            return RagQueryResponse(answer=_FALLBACK_ANSWER, citations=[], retrieved_chunks=[])

        chunk_texts = [r.chunk_text for r in retrieval_response.results]
        context = assemble_context_block(chunk_texts)
        prompt = build_grounded_rag_prompt(question=query, context=context)

        if self._llm_complete is not None:
            answer = self._llm_complete(prompt)
        else:
            answer = _openai_chat_completion(prompt, model=self._chat_model)

        chunk_citations = citations_from_query_results(retrieval_response.results)
        citations = [
            Citation(
                chunk_id=c.chunk_id,
                document_id=c.document_id,
                chunk_text_snippet=c.chunk_text_snippet,
                score=c.score,
            )
            for c in chunk_citations
        ]
        retrieved_chunks = [
            RetrievedChunkSummary(
                chunk_id=c.chunk_id,
                document_id=c.document_id,
                chunk_text_snippet=c.chunk_text_snippet,
                score=c.score,
            )
            for c in chunk_citations
        ]
        return RagQueryResponse(answer=answer.strip(), citations=citations, retrieved_chunks=retrieved_chunks)
