"""Discover supported document files under a directory tree."""

from __future__ import annotations

from pathlib import Path

# MVP: Markdown and plain text only.
SUPPORTED_SUFFIXES: frozenset[str] = frozenset({".md", ".txt"})


def iter_supported_files(root: Path) -> list[Path]:
    """
    Recursively find supported document files under ``root``.

    Only regular files whose suffix is in :data:`SUPPORTED_SUFFIXES` (case-insensitive)
    are included. Results are sorted by resolved path string for deterministic ordering.

    Args:
        root: Directory to scan. Must exist and be a directory.

    Returns:
        Sorted list of file paths (absolute after resolution).

    Raises:
        NotADirectoryError: If ``root`` is not a directory.
        FileNotFoundError: If ``root`` does not exist.
    """
    resolved = root.resolve()
    if not resolved.is_dir():
        raise NotADirectoryError(f"Not a directory: {root}")

    found: list[Path] = []
    for path in resolved.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in SUPPORTED_SUFFIXES:
            continue
        found.append(path)

    return sorted(found, key=lambda p: str(p))
