"""Split plain text into fixed-size overlapping chunks."""

from __future__ import annotations


def chunk_text(text: str, chunk_size: int, overlap: int) -> list[tuple[int, str]]:
    """
    Split ``text`` into overlapping character chunks.

    Chunks are produced by sliding a window of ``chunk_size`` characters. After each
    chunk (except when the end of ``text`` is reached), the window advances by
    ``chunk_size - overlap`` characters. This yields deterministic output for the same
    inputs and is stable across runs.

    Args:
        text: Input string (may be empty).
        chunk_size: Maximum number of characters per chunk; must be positive.
        overlap: Number of characters shared with the next chunk; must satisfy
            ``0 <= overlap < chunk_size``.

    Returns:
        List of ``(chunk_index, chunk_text)`` pairs. ``chunk_index`` starts at 0 and
        increments by one per chunk. Empty ``text`` produces an empty list.

    Raises:
        ValueError: If ``chunk_size`` or ``overlap`` are invalid.
    """
    if chunk_size <= 0:
        raise ValueError(f"chunk_size must be positive, got {chunk_size}")
    if overlap < 0:
        raise ValueError(f"overlap must be non-negative, got {overlap}")
    if overlap >= chunk_size:
        raise ValueError(
            f"overlap must be less than chunk_size (got overlap={overlap}, chunk_size={chunk_size})"
        )

    if not text:
        return []

    stride = chunk_size - overlap
    out: list[tuple[int, str]] = []
    start = 0
    idx = 0
    n = len(text)

    while start < n:
        chunk = text[start : start + chunk_size]
        out.append((idx, chunk))
        idx += 1
        if start + chunk_size >= n:
            break
        start += stride

    return out
