"""Application settings, loaded from environment / .env."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration. Values come from the environment or a local .env."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Database (async driver used by the app at runtime).
    database_url: str = Field(
        default="postgresql+asyncpg://vasp:vasp@localhost:5432/vasp",
        alias="DATABASE_URL",
    )

    # Cache.
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

    # Chain providers (unused while running offline fixtures).
    etherscan_api_key: str = Field(default="", alias="ETHERSCAN_API_KEY")
    etherscan_base_url: str = Field(
        default="https://api.etherscan.io/api", alias="ETHERSCAN_BASE_URL"
    )
    rpc_url: str = Field(default="", alias="RPC_URL")

    # Attribution engine.
    model_version: str = Field(default="phase1-dev", alias="MODEL_VERSION")
    confidence_threshold: float = Field(default=0.55, alias="CONFIDENCE_THRESHOLD")

    # App.
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    env: str = Field(default="development", alias="ENV")

    @property
    def sync_database_url(self) -> str:
        """Sync SQLAlchemy URL derived from the async one (used by Alembic)."""
        return self.database_url.replace("+asyncpg", "+psycopg")


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
