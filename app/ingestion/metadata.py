"""Metadata extraction helpers for ingested documents."""

from __future__ import annotations

from pathlib import Path

TEAM_KEYWORDS: dict[str, tuple[str, ...]] = {
    "Platform": ("platform", "gateway", "infra", "infrastructure", "deployment"),
    "Security": ("security", "auth", "authentication", "iam", "policy"),
    "Billing": ("billing", "invoice", "payment", "pricing", "charge"),
    "SRE": ("sre", "incident", "runbook", "oncall", "on-call"),
}


def _humanize_title(stem: str) -> str:
    """Convert a filename stem into a readable title."""
    cleaned = stem.replace("_", " ").replace("-", " ").strip()
    return cleaned.title()


def infer_team(path: Path) -> str | None:
    """
    Infer an owning team from path tokens.

    Matching is keyword-based and deterministic. The first matching team in
    ``TEAM_KEYWORDS`` declaration order is returned.
    """
    haystack = str(path).lower()
    for team, keywords in TEAM_KEYWORDS.items():
        if any(keyword in haystack for keyword in keywords):
            return team
    return None


def extract_metadata(file_path: Path, source_root: Path | None = None) -> dict[str, str | None]:
    """
    Extract basic metadata from a document path.

    Metadata includes:
    - ``doc_type``: parent folder name (e.g., architecture, runbooks)
    - ``title``: humanized filename stem
    - ``source_path``: relative path when ``source_root`` is provided, else absolute path
    - ``team``: optional inferred owning team

    Args:
        file_path: Source file path.
        source_root: Optional root to relativize ``source_path``.

    Returns:
        A metadata dictionary suitable for document creation.
    """
    resolved_file = file_path.resolve()
    doc_type = resolved_file.parent.name or None
    title = _humanize_title(resolved_file.stem)

    if source_root is None:
        source_path = str(resolved_file)
    else:
        resolved_root = source_root.resolve()
        try:
            source_path = str(resolved_file.relative_to(resolved_root))
        except ValueError:
            source_path = str(resolved_file)

    return {
        "doc_type": doc_type,
        "title": title,
        "source_path": source_path,
        "team": infer_team(resolved_file),
    }
