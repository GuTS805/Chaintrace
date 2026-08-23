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

    # ---- Chain providers (unused while running offline fixtures) ----
    etherscan_api_key: str = Field(default="", alias="ETHERSCAN_API_KEY")
    etherscan_base_url: str = Field(
        default="https://api.etherscan.io/api", alias="ETHERSCAN_BASE_URL"
    )
    blockscout_base_url: str = Field(
        default="https://eth.blockscout.com/api", alias="BLOCKSCOUT_BASE_URL"
    )
    alchemy_api_key: str = Field(default="", alias="ALCHEMY_API_KEY")
    alchemy_base_url: str = Field(
        default="https://eth-mainnet.g.alchemy.com/v2", alias="ALCHEMY_BASE_URL"
    )
    infura_api_key: str = Field(default="", alias="INFURA_API_KEY")
    infura_base_url: str = Field(
        default="https://mainnet.infura.io/v3", alias="INFURA_BASE_URL"
    )
    rpc_url: str = Field(default="", alias="RPC_URL")

    # Failover order, most-preferred first. Providers whose credentials are
    # missing are skipped when the router is built, so this can list everything.
    provider_order: str = Field(
        default="etherscan,blockscout,alchemy,infura", alias="PROVIDER_ORDER"
    )
    # Blockscout needs no key, so it would otherwise be enabled everywhere --
    # including offline runs that must make no network calls at all.
    provider_allow_keyless: bool = Field(
        default=False, alias="PROVIDER_ALLOW_KEYLESS"
    )

    # ---- Provider resilience ----
    provider_timeout_seconds: float = Field(default=15.0, alias="PROVIDER_TIMEOUT")
    provider_max_attempts: int = Field(default=3, alias="PROVIDER_MAX_ATTEMPTS")
    provider_failure_threshold: int = Field(
        default=3, alias="PROVIDER_FAILURE_THRESHOLD"
    )
    provider_recovery_seconds: float = Field(
        default=30.0, alias="PROVIDER_RECOVERY_SECONDS"
    )
    provider_page_size: int = Field(default=200, alias="PROVIDER_PAGE_SIZE")

    # ---- Provider cache ----
    provider_cache_enabled: bool = Field(default=True, alias="PROVIDER_CACHE_ENABLED")
    provider_cache_ttl_seconds: int = Field(
        default=900, alias="PROVIDER_CACHE_TTL_SECONDS"
    )

    # Attribution engine.
    model_version: str = Field(default="phase1-dev", alias="MODEL_VERSION")
    confidence_threshold: float = Field(default=0.55, alias="CONFIDENCE_THRESHOLD")

    # App.
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    env: str = Field(default="development", alias="ENV")
    cors_origins: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000",
        alias="CORS_ORIGINS",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def provider_order_list(self) -> list[str]:
        return [p.strip().lower() for p in self.provider_order.split(",") if p.strip()]

    @property
    def sync_database_url(self) -> str:
        """Sync SQLAlchemy URL derived from the async one (used by Alembic)."""
        return self.database_url.replace("+asyncpg", "+psycopg")


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
