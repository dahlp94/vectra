"""Application settings loaded from environment and optional `.env` file."""

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration; extend with new fields as features are added."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # App
    app_env: str = Field(default="local", description="Deployment environment name.")
    log_level: str = Field(default="INFO", description="Root log level (e.g. DEBUG, INFO).")

    # Database
    database_url: str = Field(
        ...,
        description="SQLAlchemy database URL (e.g. postgresql+psycopg2://...).",
    )
    sqlalchemy_echo: bool = Field(
        default=False,
        description="If True, log SQL statements (useful for local debugging).",
    )

    # Embeddings (used in later batches; optional in .env until wired)
    embedding_provider: str = Field(default="openai")
    embedding_model: str = Field(default="text-embedding-3-small")
    embedding_dimension: int = Field(default=1536, ge=1)
    openai_api_key: str | None = Field(default=None)

    @field_validator("log_level")
    @classmethod
    def normalize_log_level(cls, value: str) -> str:
        upper = value.strip().upper()
        valid = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"}
        if upper not in valid:
            raise ValueError(f"log_level must be one of {sorted(valid)}, got {value!r}")
        return upper

    @field_validator("openai_api_key", mode="before")
    @classmethod
    def empty_openai_key_to_none(cls, value: object) -> object:
        if value == "":
            return None
        return value


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton (call `get_settings.cache_clear()` in tests if needed)."""
    return Settings()
