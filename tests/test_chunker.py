"""Tests for ``app.ingestion.chunker.chunk_text``."""

from __future__ import annotations

import pytest

from app.ingestion.chunker import chunk_text


def test_chunk_size_caps_each_segment_length() -> None:
    text = "a" * 200
    chunk_size = 37
    overlap = 5
    segments = chunk_text(text, chunk_size, overlap)
    for _index, segment in segments:
        assert len(segment) <= chunk_size


def test_overlap_is_shared_between_consecutive_chunks() -> None:
    text = "0123456789" * 8  # 80 chars, predictable pattern
    chunk_size = 12
    overlap = 4
    segments = chunk_text(text, chunk_size, overlap)
    assert len(segments) >= 2
    for i in range(len(segments) - 1):
        left = segments[i][1]
        right = segments[i + 1][1]
        assert left[-overlap:] == right[:overlap]


def test_output_is_deterministic_for_identical_inputs() -> None:
    text = "alpha beta gamma delta " * 15
    first = chunk_text(text, chunk_size=64, overlap=12)
    second = chunk_text(text, chunk_size=64, overlap=12)
    assert first == second


def test_non_empty_text_produces_only_non_empty_chunks() -> None:
    text = "z" * 120
    segments = chunk_text(text, chunk_size=25, overlap=8)
    assert segments
    for _index, segment in segments:
        assert len(segment) > 0


def test_chunk_indices_are_sequential_from_zero() -> None:
    text = "abcdefghij" * 5
    segments = chunk_text(text, chunk_size=7, overlap=2)
    assert [idx for idx, _ in segments] == list(range(len(segments)))


def test_empty_string_returns_empty_list() -> None:
    assert chunk_text("", chunk_size=10, overlap=2) == []


def test_invalid_overlap_raises() -> None:
    with pytest.raises(ValueError):
        chunk_text("abc", chunk_size=3, overlap=3)
