"""Shared FastAPI dependencies (settings, DB session, etc.)."""

from typing import Annotated

from fastapi import Depends

from app.core.config import Settings, get_settings


def get_settings_dep() -> Settings:
    """Return cached application settings for injection into routes and services."""
    return get_settings()


SettingsDep = Annotated[Settings, Depends(get_settings_dep)]
