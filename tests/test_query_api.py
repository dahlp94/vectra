"""Tests for the RAG ``/query`` endpoint and ``RAGService`` orchestration."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes.query import router as query_router
from app.rag.service import RAGService, _FALLBACK_ANSWER
from app.schemas.query import (
    Citation,
    QueryResponse,
    QueryResult,
    RagQueryResponse,
    RetrievedChunkSummary,
)


def _sample_result(*, score: float = 0.91) -> QueryResult:
    return QueryResult(
        chunk_id=uuid4(),
        document_id=uuid4(),
        chunk_text="Acme Corp requires two-factor authentication for all VPN access.",
        score=score,
    )


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    app.include_router(query_router)
    return TestClient(app)


def test_post_query_returns_structured_response(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """POST /query returns JSON with answer, citations, and retrieved_chunks."""
    cid = uuid4()
    did = uuid4()
    snippet = "Acme Corp requires two-factor authentication"

    class _StubRAG:
        def __init__(self, _session: Any) -> None:
            pass

        def complete_query(
            self,
            query: str,
            top_k: int | None = None,
            filters: dict[str, Any] | None = None,
        ) -> RagQueryResponse:
            return RagQueryResponse(
                answer="Two-factor authentication is required for VPN access.",
                citations=[
                    Citation(
                        chunk_id=cid,
                        document_id=did,
                        chunk_text_snippet=snippet,
                        score=0.91,
                    )
                ],
                retrieved_chunks=[
                    RetrievedChunkSummary(
                        chunk_id=cid,
                        document_id=did,
                        chunk_text_snippet=snippet,
                        score=0.91,
                    )
                ],
            )

    monkeypatch.setattr("app.api.routes.query.RAGService", _StubRAG)
    response = client.post(
        "/query",
        json={"query": "What is required for VPN?", "top_k": 3},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "Two-factor authentication is required for VPN access."
    assert len(data["citations"]) == 1
    assert data["citations"][0]["chunk_id"] == str(cid)
    assert data["citations"][0]["document_id"] == str(did)
    assert data["citations"][0]["chunk_text_snippet"] == snippet
    assert data["citations"][0]["score"] == pytest.approx(0.91)
    assert len(data["retrieved_chunks"]) == 1
    assert data["retrieved_chunks"][0]["chunk_id"] == str(cid)
    assert data["retrieved_chunks"][0]["document_id"] == str(did)
    assert data["retrieved_chunks"][0]["chunk_text_snippet"] == snippet


def test_post_query_returns_fallback_response_via_route(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """API returns structured fallback (empty citations/chunks) when service has no context."""
    class _StubFallbackRAG:
        def __init__(self, _session: Any) -> None:
            pass

        def complete_query(
            self,
            query: str,
            top_k: int | None = None,
            filters: dict[str, Any] | None = None,
        ) -> RagQueryResponse:
            return RagQueryResponse(
                answer=_FALLBACK_ANSWER,
                citations=[],
                retrieved_chunks=[],
            )

    monkeypatch.setattr("app.api.routes.query.RAGService", _StubFallbackRAG)
    response = client.post("/query", json={"query": "Unknown topic xyz"})
    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == _FALLBACK_ANSWER
    assert data["citations"] == []
    assert data["retrieved_chunks"] == []


def test_post_query_value_error_returns_400(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    class _BadRAG:
        def __init__(self, _session: Any) -> None:
            pass

        def complete_query(
            self,
            query: str,
            top_k: int | None = None,
            filters: dict[str, Any] | None = None,
        ) -> RagQueryResponse:
            raise ValueError("invalid filter")

    monkeypatch.setattr("app.api.routes.query.RAGService", _BadRAG)
    response = client.post("/query", json={"query": "hello"})
    assert response.status_code == 400
    assert "invalid filter" in response.json()["detail"]


def test_post_query_runtime_error_returns_502(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    class _FailingRAG:
        def __init__(self, _session: Any) -> None:
            pass

        def complete_query(
            self,
            query: str,
            top_k: int | None = None,
            filters: dict[str, Any] | None = None,
        ) -> RagQueryResponse:
            raise RuntimeError("upstream unavailable")

    monkeypatch.setattr("app.api.routes.query.RAGService", _FailingRAG)
    response = client.post("/query", json={"query": "hello"})
    assert response.status_code == 502
    assert "upstream unavailable" in response.json()["detail"]


def test_retrieval_runs_before_llm() -> None:
    """RAGService invokes retrieval before the LLM when context is sufficient."""
    order: list[str] = []

    class _FakeRetrieval:
        def retrieve(
            self,
            query: str,
            top_k: int | None = None,
            filters: dict[str, Any] | None = None,
        ) -> QueryResponse:
            order.append("retrieve")
            return QueryResponse(results=[_sample_result()])

    def fake_llm(prompt: str) -> str:
        order.append("llm")
        return "ok"

    svc = RAGService(
        None,
        retrieval_service=_FakeRetrieval(),
        llm_complete=fake_llm,
    )
    svc.complete_query("test")
    assert order == ["retrieve", "llm"]


def test_no_context_returns_fallback_without_llm() -> None:
    """Empty retrieval yields the configured fallback string and skips the LLM."""
    llm_called = False

    class _EmptyRetrieval:
        def retrieve(
            self,
            query: str,
            top_k: int | None = None,
            filters: dict[str, Any] | None = None,
        ) -> QueryResponse:
            return QueryResponse(results=[])

    def fake_llm(_: str) -> str:
        nonlocal llm_called
        llm_called = True
        return "should not run"

    svc = RAGService(
        None,
        retrieval_service=_EmptyRetrieval(),
        llm_complete=fake_llm,
    )
    out = svc.complete_query("anything")
    assert isinstance(out, RagQueryResponse)
    assert out.answer == _FALLBACK_ANSWER
    assert out.citations == []
    assert out.retrieved_chunks == []
    assert llm_called is False


def test_low_score_returns_fallback_without_llm() -> None:
    """Scores below the relevance threshold behave like no useful context."""
    llm_called = False

    class _WeakRetrieval:
        def retrieve(
            self,
            query: str,
            top_k: int | None = None,
            filters: dict[str, Any] | None = None,
        ) -> QueryResponse:
            return QueryResponse(results=[_sample_result(score=0.05)])

    def fake_llm(_: str) -> str:
        nonlocal llm_called
        llm_called = True
        return "should not run"

    svc = RAGService(
        None,
        retrieval_service=_WeakRetrieval(),
        llm_complete=fake_llm,
    )
    out = svc.complete_query("vague")
    assert out.answer == _FALLBACK_ANSWER
    assert out.citations == []
    assert out.retrieved_chunks == []
    assert llm_called is False


def test_query_request_validation(client: TestClient) -> None:
    """Empty query string is rejected by the schema."""
    response = client.post("/query", json={"query": ""})
    assert response.status_code == 422
