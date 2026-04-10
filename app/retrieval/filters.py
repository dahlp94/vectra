"""Minimal metadata filter helpers for retrieval queries."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sqlalchemy.sql.elements import ColumnElement

from app.db.models import Document

SUPPORTED_FILTER_KEYS: frozenset[str] = frozenset({"doc_type", "team", "source_path"})


def normalize_metadata_filters(raw_filters: Mapping[str, Any] | None) -> dict[str, str]:
    """
    Keep supported string filters only, trimming whitespace values.

    Args:
        raw_filters: Arbitrary incoming filter payload.

    Returns:
        Dictionary of validated metadata filters.
    """
    if not raw_filters:
        return {}

    normalized: dict[str, str] = {}
    for key in SUPPORTED_FILTER_KEYS:
        value = raw_filters.get(key)
        if isinstance(value, str):
            cleaned = value.strip()
            if cleaned:
                normalized[key] = cleaned
    return normalized


def build_document_filter_clauses(
    metadata_filters: Mapping[str, str] | None,
) -> list[ColumnElement[bool]]:
    """
    Convert metadata filters into SQLAlchemy WHERE clauses on ``Document``.

    Args:
        metadata_filters: Pre-normalized filters (or raw mapping).

    Returns:
        A list of SQLAlchemy boolean expressions for use in a query.
    """
    normalized = normalize_metadata_filters(metadata_filters)
    clauses: list[ColumnElement[bool]] = []

    if "doc_type" in normalized:
        clauses.append(Document.doc_type == normalized["doc_type"])
    if "team" in normalized:
        clauses.append(Document.team == normalized["team"])
    if "source_path" in normalized:
        clauses.append(Document.source_path == normalized["source_path"])

    return clauses
