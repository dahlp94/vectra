"""SQLAlchemy declarative base for ORM models."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Subclass for all SQLAlchemy models (Alembic autogenerate will discover these)."""

    pass
