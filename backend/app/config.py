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
    # Keyless Etherscan-compatible endpoint used by the live "trace any wallet"
    # feature. Blockscout requires no API key.
    blockscout_base_url: str = Field(
        default="https://eth.blockscout.com/api", alias="BLOCKSCOUT_BASE_URL"
    )
    # Same Blockscout instance software, different EVM chain — same keyless
    # account/txlist + tokentx schema, just a different base URL. (BNB Smart
    # Chain has no public Blockscout instance and BscScan's keyless API was
    # retired, so it isn't offered here — would need a paid/free-tier key.)
    polygon_blockscout_base_url: str = Field(
        default="https://polygon.blockscout.com/api", alias="POLYGON_BLOCKSCOUT_BASE_URL"
    )
    # TronGrid: keyless like Blockscout for low-volume use; an optional API key
    # (header, not this URL) only raises rate limits.
    trongrid_base_url: str = Field(
        default="https://api.trongrid.io", alias="TRONGRID_BASE_URL"
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

    # Auth (officer login). The default secret is fine for the offline demo
    # (single-machine, no real case data); override JWT_SECRET for any
    # non-demo deployment.
    jwt_secret: str = Field(
        default="chaintrace-demo-secret-change-in-production", alias="JWT_SECRET"
    )
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_expire_minutes: int = Field(default=480, alias="JWT_EXPIRE_MINUTES")

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def sync_database_url(self) -> str:
        """Sync SQLAlchemy URL derived from the async one (used by Alembic)."""
        return self.database_url.replace("+asyncpg", "+psycopg")


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
