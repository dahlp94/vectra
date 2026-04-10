"""Deterministic prompt construction for grounded RAG answers (no LLM calls)."""

from __future__ import annotations

from collections.abc import Sequence

_DEFAULT_CONTEXT_SEPARATOR = "\n\n---\n\n"

_GROUNDING_INSTRUCTIONS = """You are answering using only the information in the CONTEXT section below.

Rules:
- Use only facts that are clearly supported by the CONTEXT. Do not use outside knowledge.
- If the CONTEXT does not contain enough information to answer, reply exactly with: I don't know based on the provided documents.
- Be concise and direct. If you cite details, they must come from the CONTEXT."""


def normalize_question(question: str) -> str:
    """Strip surrounding whitespace from the user question."""
    return question.strip()


def assemble_context_block(chunk_texts: Sequence[str], *, separator: str = _DEFAULT_CONTEXT_SEPARATOR) -> str:
    """
    Join chunk texts into a single context block for prompting.

    Empty strings are skipped so the block stays clean and deterministic.
    """
    parts: list[str] = []
    for text in chunk_texts:
        cleaned = text.strip()
        if cleaned:
            parts.append(cleaned)
    return separator.join(parts)


def build_grounded_rag_prompt(*, question: str, context: str) -> str:
    """
    Build a full user message / prompt body for a grounded answer.

    The caller is responsible for ensuring ``context`` is non-empty before
    invoking an LLM; this function does not embed retrieval logic.

    Args:
        question: User question (leading/trailing whitespace is stripped).
        context: Retrieved document text assembled into one block.

    Returns:
        A single prompt string combining instructions, context, and question.
    """
    q = normalize_question(question)
    ctx = context.strip()
    return (
        f"{_GROUNDING_INSTRUCTIONS}\n\n"
        f"CONTEXT:\n{ctx}\n\n"
        f"QUESTION:\n{q}"
    )
