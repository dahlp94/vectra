"""Application-wide logging setup (stdlib only, suitable for local and container runs)."""

from __future__ import annotations

import logging
import sys
from typing import Final

from app.core.config import Settings, get_settings

_LOG_FORMAT: Final[str] = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT: Final[str] = "%Y-%m-%d %H:%M:%S"


def configure_logging(settings: Settings | None = None) -> None:
    """
    Configure the root logger once: stdout handler and a consistent line format.

    Idempotent: if handlers already exist on the root logger, only the level is updated.
    """
    cfg = settings if settings is not None else get_settings()
    level = getattr(logging, cfg.log_level, logging.INFO)

    root = logging.getLogger()
    root.setLevel(level)

    if not root.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        formatter = logging.Formatter(fmt=_LOG_FORMAT, datefmt=_DATE_FORMAT)
        handler.setFormatter(formatter)
        root.addHandler(handler)

    # Reduce noise from libraries unless debugging SQL.
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if cfg.sqlalchemy_echo else logging.WARNING
    )
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
