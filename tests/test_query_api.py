"""Week 5 — RAG /query API smoke and behavior tests."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes.query import router as query_router
from app.rag.service import RAGService
from app.schemas.query import (
    Citation,
    QueryResponse,
    QueryResult,
    RagQueryResponse,
    RetrievedChunkSummary,
)


def _sample_result() -> QueryResult:
    return QueryResult(
        chunk_id=uuid4(),
        document_id=uuid4(),
        chunk_text="Acme Corp requires two-factor authentication for all VPN access.",
        score=0.91,
    )


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    app.include_router(query_router)
    return TestClient(app)


def test_post_query_returns_structured_response(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """POST /query returns answer, citations, and retrieved_chunks."""
    cid = uuid4()
    did = uuid4()

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
                        chunk_text_snippet="Acme Corp requires two-factor authentication",
                        score=0.91,
                    )
                ],
                retrieved_chunks=[
                    RetrievedChunkSummary(
                        chunk_id=cid,
                        document_id=did,
                        chunk_text_snippet="Acme Corp requires two-factor authentication",
                        score=0.91,
                    )
                ],
            )

    monkeypatch.setattr("app.api.routes.query.RAGService", _StubRAG)
    response = client.post("/query", json={"query": "What is required for VPN?", "top_k": 3})
    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "Two-factor authentication is required for VPN access."
    assert len(data["citations"]) == 1
    assert data["citations"][0]["chunk_text_snippet"]
    assert data["citations"][0]["score"] == pytest.approx(0.91)
    assert len(data["retrieved_chunks"]) == 1
    assert data["retrieved_chunks"][0]["chunk_id"] == str(cid)


def test_retrieval_runs_before_llm() -> None:
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


def test_no_context_returns_fallback() -> None:
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
    assert "No relevant passages" in out.answer
    assert out.citations == []
    assert out.retrieved_chunks == []
    assert llm_called is False


def test_query_request_validation(client: TestClient) -> None:
    response = client.post("/query", json={"query": ""})
    assert response.status_code == 422
