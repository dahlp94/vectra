"""Create application tables from SQLAlchemy models."""

from __future__ import annotations

from sqlalchemy.engine import Engine

from app.db.base import Base
from app.db.session import get_engine

# Import models so they are registered on ``Base.metadata`` before ``create_all``.
from app.db import models as _models  # noqa: F401


def create_tables(engine: Engine | None = None) -> None:
    """
    Create all tables defined on ``Base.metadata`` if they do not exist.

    Postgres must have the ``vector`` extension enabled (see ``sql/init_pgvector.sql``
    and the Docker init script).
    """
    bind = engine if engine is not None else get_engine()
    Base.metadata.create_all(bind=bind)
