"""Deterministic prompt construction for grounded RAG answers (no LLM calls)."""

from __future__ import annotations

from collections.abc import Sequence

_CHUNK_SEPARATOR = "\n\n---\n\n"

_GROUNDING_INSTRUCTIONS = """You are answering using ONLY the information in the CONTEXT section below.

Rules:
- Use ONLY the provided context. Do not use prior knowledge or assumptions.
- Do NOT reference documents, file paths, URLs, section titles, or sources that are not explicitly present in the context text.
- If the answer is not directly supported by the context, respond with exactly: I don't know based on the provided documents.
- Be concise. Every factual claim must be traceable to the numbered passages below."""


def normalize_question(question: str) -> str:
    """Strip surrounding whitespace from the user question."""
    return question.strip()


def assemble_context_block(chunk_texts: Sequence[str], *, separator: str = _CHUNK_SEPARATOR) -> str:
    """
    Join chunk texts into a single numbered context block for prompting.

    Non-empty chunks are labeled ``[1]``, ``[2]``, ... so boundaries stay clear for the model.
    Empty strings are skipped.
    """
    parts: list[str] = []
    index = 1
    for text in chunk_texts:
        cleaned = text.strip()
        if cleaned:
            parts.append(f"[{index}]\n{cleaned}")
            index += 1
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
        f"CONTEXT (numbered passages; use only these):\n{ctx}\n\n"
        f"QUESTION:\n{q}"
    )
