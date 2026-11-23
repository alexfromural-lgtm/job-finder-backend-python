# =============================================================================
# app/config.py  —  CENTRALISED ENVIRONMENT CONFIGURATION
# =============================================================================
# All environment variables are read ONCE here and exposed as typed Python
# attributes on the `settings` singleton.
#
# WHY NOT `os.getenv()` EVERYWHERE?
#   • Single source of truth — if a var name changes you fix it in one place.
#   • Validation at startup — the app crashes immediately with a clear error
#     instead of silently using a None/wrong value deep in a request.
#   • Type safety — integers stay int, booleans stay bool, etc.
#
# LEARNING CONCEPT ► Pydantic Settings
#   pydantic-settings extends Pydantic's data-validation library.
#   `BaseSettings` reads values from environment variables (and optionally a
#   .env file), then validates + coerces them into typed fields.
#
#   EXAMPLE:
#     class MySettings(BaseSettings):
#         PORT: int = 8000      # reads $PORT, casts to int, defaults to 8000
#         DEBUG: bool = False   # reads $DEBUG, casts "true"/"1" → True
#     settings = MySettings()   # do this ONCE at module level
# =============================================================================

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from typing import Optional
import sys


class Settings(BaseSettings):
    """
    Centralised, validated environment configuration.
    All env reads live here — the rest of the codebase works with typed
    constants rather than raw os.getenv() calls.
    The app exits immediately at startup if required vars are missing or invalid.

    Mirrors src/config/env.ts in the Node.js project.
    """

    # -------------------------------------------------------------------------
    # `model_config` controls how pydantic-settings behaves:
    #   env_file=".env"   → also read from a .env file (like python-dotenv)
    #   extra="ignore"    → silently ignore extra env vars we don't declare
    #
    # LEARNING EXAMPLE ► case sensitivity:
    #   By default pydantic-settings is case-insensitive on most platforms,
    #   so PORT, port, and Port all map to the `PORT` field.
    # -------------------------------------------------------------------------
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ── Server ────────────────────────────────────────────────────────────────
    PORT: int = 5002           # Uvicorn listens on this port
    APP_ENV: str = "development"

    # ── Database ──────────────────────────────────────────────────────────────
    # Required (no default) — startup fails if DATABASE_URL is not set.
    # Format: postgresql+asyncpg://user:password@host:port/dbname
    DATABASE_URL: str

    # ── JWT ───────────────────────────────────────────────────────────────────
    ACCESS_TOKEN_SECRET: str           # Secret key to sign access JWTs
    ACCESS_TOKEN_EXPIRES_IN: str = "15m"   # e.g. "15m", "1h", "7d"
    REFRESH_TOKEN_SECRET: str          # Separate secret for refresh JWTs
    REFRESH_TOKEN_EXPIRES_IN: str = "7d"
    REFRESH_TOKEN_MAX_AGE_MS: int = 7 * 24 * 60 * 60 * 1000  # cookie Max-Age

    # ── CORS ──────────────────────────────────────────────────────────────────
    # The URL of the frontend (e.g. "http://localhost:3000").
    CORS_ORIGIN: Optional[str] = None

    # ── Redis / Queue ─────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"
    QUEUE_CONCURRENCY: int = 5  # how many Celery worker threads run in parallel

    # =========================================================================
    # VALIDATORS
    # =========================================================================
    # `@field_validator` runs after the field value is read from the environment.
    # It can raise ValueError (which pydantic turns into a startup error) or
    # return the transformed value.
    #
    # LEARNING EXAMPLE ► validator that normalises a URL:
    #   @field_validator("DATABASE_URL")
    #   @classmethod
    #   def normalise_db_url(cls, v):
    #       return v.rstrip("/")   # remove trailing slash
    # =========================================================================

    @field_validator("ACCESS_TOKEN_SECRET", "REFRESH_TOKEN_SECRET")
    @classmethod
    def secrets_not_empty(cls, v: str) -> str:
        """Reject empty or whitespace-only secrets — that's a security hole."""
        if not v.strip():
            raise ValueError("JWT secret must not be empty")
        return v

    # =========================================================================
    # COMPUTED PROPERTIES
    # =========================================================================
    # `@property` turns a method into a read-only attribute.
    # These are derived from the raw env fields above.
    #
    # LEARNING EXAMPLE ► property usage:
    #   settings.is_production   # True when APP_ENV == "production"
    #   settings.access_token_expire_seconds  # 900 (15 minutes in seconds)
    # =========================================================================

    @property
    def is_development(self) -> bool:
        return self.APP_ENV == "development"

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def access_token_expire_seconds(self) -> int:
        """
        Parse a human-readable duration string (e.g. "15m", "1h", "7d")
        into seconds for use in JWT `exp` claims.

        LEARNING NOTE ► JWT `exp` is Unix timestamp (seconds since epoch),
        not a duration string — that's why we convert here.
        """
        return _parse_duration(self.ACCESS_TOKEN_EXPIRES_IN)

    @property
    def refresh_token_expire_seconds(self) -> int:
        return _parse_duration(self.REFRESH_TOKEN_EXPIRES_IN)


# =============================================================================
# HELPER: duration string parser
# =============================================================================
# Parses strings like "15m", "1h", "7d" into an integer number of seconds.
#
# LEARNING EXAMPLE ► manual testing:
#   _parse_duration("30s")  →  30
#   _parse_duration("2h")   →  7200
#   _parse_duration("1d")   →  86400
# =============================================================================
def _parse_duration(s: str) -> int:
    units = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    s = s.strip()
    suffix = s[-1].lower()
    if suffix in units:
        return int(s[:-1]) * units[suffix]
    # Assume raw seconds if no unit suffix
    return int(s)


# =============================================================================
# SINGLETON
# =============================================================================
# `Settings()` reads .env + environment variables RIGHT NOW at import time.
# If a required variable is missing, pydantic raises ValidationError and the
# process exits before the HTTP server even starts.
#
# IMPORTANT: import `settings` from here, never re-create `Settings()`.
# =============================================================================
try:
    settings = Settings()  # type: ignore[call-arg]
except Exception as exc:
    # Print a human-readable error and exit with a non-zero code so Docker /
    # systemd / kubernetes knows the process failed to start.
    print(f"[CONFIG ERROR] Failed to load environment settings:\n  {exc}", file=sys.stderr)
    sys.exit(1)
