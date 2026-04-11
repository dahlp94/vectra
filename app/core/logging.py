"""Application-wide logging setup (stdlib only, suitable for local and container runs).

Use :func:`configure_logging` once at process startup (CLI scripts, ASGI factory if desired).
Use :func:`get_logger` inside modules for consistent, namespaced loggers:

- ``api`` — HTTP routes and request handling
- ``ingestion`` — folder discovery, parsing, chunking, pipeline orchestration
- ``embeddings`` — embedding provider calls and batching
- ``retrieval`` — query embedding and vector search
- ``rag`` — RAG orchestration and LLM completion

Example::

    from app.core.logging import configure_logging, get_logger

    configure_logging()
    log = get_logger("ingestion")
    log.info("Ingesting folder: %s", folder_path)
"""

from __future__ import annotations

import logging
import sys
from typing import Final

from app.core.config import Settings, get_settings

_LOG_FORMAT: Final[str] = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT: Final[str] = "%Y-%m-%d %H:%M:%S"

LOG_NAMESPACE: Final[str] = "vectra"


def get_logger(component: str) -> logging.Logger:
    """
    Return a namespaced logger for a subsystem (e.g. ``vectra.ingestion``).

    Args:
        component: Short label such as ``ingestion`` or ``retrieval`` (no leading ``vectra.``).

    Raises:
        ValueError: If ``component`` is empty after stripping.
    """
    safe = component.strip().strip(".")
    if not safe:
        raise ValueError("component must be a non-empty string")
    return logging.getLogger(f"{LOG_NAMESPACE}.{safe}")


def configure_logging(settings: Settings | None = None) -> None:
    """
    Configure the root logger: single stdout handler and a readable line format.

    Idempotent: if handlers already exist on the root logger, only levels are updated.

    Reduces noise from SQLAlchemy, Uvicorn access, and HTTP client libraries unless
    ``sqlalchemy_echo`` is enabled in settings (SQL detail).
    """
    cfg = settings if settings is not None else get_settings()
    level = getattr(logging, cfg.log_level, logging.INFO)

    root = logging.getLogger()
    root.setLevel(level)

    if not root.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        handler.setFormatter(logging.Formatter(fmt=_LOG_FORMAT, datefmt=_DATE_FORMAT))
        root.addHandler(handler)

    # SQLAlchemy: surface SQL only when explicitly enabled.
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if cfg.sqlalchemy_echo else logging.WARNING
    )
    logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)

    # Uvicorn: errors at INFO; access lines stay quiet for local demos.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)

    # HTTP stacks used by OpenAI and similar clients.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
