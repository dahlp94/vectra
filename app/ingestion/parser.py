"""Parse supported document files into plain text for ingestion."""

from __future__ import annotations

from pathlib import Path

from app.ingestion.loader import SUPPORTED_SUFFIXES


def parse_file(path: Path) -> str:
    """
    Read a ``.md`` or ``.txt`` file and return its contents as a single string.

    For the MVP, Markdown is treated as UTF-8 text without structural parsing;
    chunking operates on this string as-is.

    Args:
        path: Path to the file.

    Returns:
        Full file contents decoded as UTF-8 (no BOM handling beyond what UTF-8 provides).

    Raises:
        ValueError: If the file suffix is not supported.
        OSError: Propagated from the filesystem if the file cannot be read.
    """
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise ValueError(
            f"Unsupported file type {suffix!r}; expected one of {sorted(SUPPORTED_SUFFIXES)}"
        )
    return path.read_text(encoding="utf-8")
