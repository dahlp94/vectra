"""Database engine and session factory."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    """Lazily construct a single Engine (pool_pre_ping for resilient connections)."""
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_engine(
            settings.database_url,
            pool_pre_ping=True,
            echo=settings.sqlalchemy_echo,
        )
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    """Shared sessionmaker bound to the application engine."""
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=get_engine(),
            expire_on_commit=False,
        )
    return _session_factory


def get_session() -> Generator[Session, None, None]:
    """
    Yield a Session and ensure it is closed after use.

    Callers (routes or services) own transaction boundaries: commit/rollback explicitly.
    Suitable for FastAPI `Depends` with a `yield` dependency.
    """
    factory = get_session_factory()
    session = factory()
    try:
        yield session
    finally:
        session.close()


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """Transactional scope for scripts/tests: commit on success, rollback on error, always close."""
    factory = get_session_factory()
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def reset_engine_and_session_factory() -> None:
    """
    Dispose of the engine and clear factories (for tests or process teardown).

    Not normally needed in application code.
    """
    global _engine, _session_factory
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _session_factory = None
