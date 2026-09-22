"""Application settings, loaded from environment / .env."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_JWT_SECRET = "chaintrace-demo-secret-change-in-production"


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

    @field_validator("database_url")
    @classmethod
    def _use_asyncpg_driver(cls, v: str) -> str:
        # Managed Postgres providers (Render, Heroku, Railway, Supabase, ...)
        # hand back a bare postgres(ql):// URL with no driver — SQLAlchemy's
        # async engine needs the asyncpg dialect spelled out explicitly.
        if v.startswith("postgres://"):
            return "postgresql+asyncpg://" + v[len("postgres://") :]
        if v.startswith("postgresql://"):
            return "postgresql+asyncpg://" + v[len("postgresql://") :]
        return v

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

    # Traversal bounds (HARD REQUIREMENT #5 — every traversal is bounded).
    # `traversal_max_nodes` is the default a caller gets when it doesn't ask
    # for a specific size (this is what ContextBuilder — i.e. every
    # /attribution and /risk request — actually uses; it previously hardcoded
    # 2000 with no config knob at all). `traversal_max_nodes_ceiling` is the
    # absolute server-side cap: a caller (e.g. the /graph API's max_nodes
    # query param) can ask for less, never more — "configurable" is not
    # "unlimited". `traversal_timeout_seconds` bounds wall-clock time, not
    # just row count, since a slow query on a large real deployment could
    # still hang a request even inside the row/node caps.
    traversal_max_nodes: int = Field(default=2000, alias="TRAVERSAL_MAX_NODES")
    traversal_max_nodes_ceiling: int = Field(
        default=10_000, alias="TRAVERSAL_MAX_NODES_CEILING"
    )
    traversal_max_hops: int = Field(default=6, alias="TRAVERSAL_MAX_HOPS")
    traversal_max_hops_ceiling: int = Field(default=8, alias="TRAVERSAL_MAX_HOPS_CEILING")
    traversal_min_value_wei: int = Field(default=0, alias="TRAVERSAL_MIN_VALUE_WEI")
    traversal_timeout_seconds: float = Field(
        default=20.0, alias="TRAVERSAL_TIMEOUT_SECONDS"
    )

    # Provider resilience (retry + circuit breaker around Blockscout/TronGrid
    # calls). A provider failure must never be reported as an attribution or
    # risk result — see app/providers/resilience.py.
    provider_max_retries: int = Field(default=2, alias="PROVIDER_MAX_RETRIES")
    provider_retry_base_delay: float = Field(
        default=0.5, alias="PROVIDER_RETRY_BASE_DELAY"
    )
    provider_circuit_failure_threshold: int = Field(
        default=3, alias="PROVIDER_CIRCUIT_FAILURE_THRESHOLD"
    )
    provider_circuit_cooldown_seconds: float = Field(
        default=30.0, alias="PROVIDER_CIRCUIT_COOLDOWN_SECONDS"
    )

    # App.
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    env: str = Field(default="development", alias="ENV")
    cors_origins: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000",
        alias="CORS_ORIGINS",
    )

    # Auth (officer login). The default secret is fine for the offline demo
    # (single-machine, no real case data); override JWT_SECRET for any
    # non-demo deployment. `env=production` with this default still set is a
    # startup-time hard failure (see app/main.py) rather than a silently
    # forgeable deployment — a comment alone doesn't stop anyone from
    # forgetting to set it.
    jwt_secret: str = Field(
        default=DEFAULT_JWT_SECRET, alias="JWT_SECRET"
    )
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_expire_minutes: int = Field(default=480, alias="JWT_EXPIRE_MINUTES")

    # Login brute-force throttling (see app/auth/rate_limit.py).
    login_max_failures: int = Field(default=5, alias="LOGIN_MAX_FAILURES")
    login_window_seconds: float = Field(default=900.0, alias="LOGIN_WINDOW_SECONDS")
    login_cooldown_seconds: float = Field(default=60.0, alias="LOGIN_COOLDOWN_SECONDS")

    # No file uploads anywhere in this API — a generous-but-bounded cap on
    # plain JSON request bodies is purely a DoS guard.
    max_request_body_bytes: int = Field(default=2_000_000, alias="MAX_REQUEST_BODY_BYTES")

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def uses_default_jwt_secret(self) -> bool:
        return self.jwt_secret == DEFAULT_JWT_SECRET

    @property
    def sync_database_url(self) -> str:
        """Sync SQLAlchemy URL derived from the async one (used by Alembic)."""
        return self.database_url.replace("+asyncpg", "+psycopg")


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
