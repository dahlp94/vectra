#!/usr/bin/env python3
"""
Create database tables for Vectra (run from repository root).

Example:
    python scripts/create_tables.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.init_db import create_tables


def main() -> None:
    configure_logging()
    get_settings()
    create_tables()
    print("Done: tables created (or already present).")


if __name__ == "__main__":
    main()
