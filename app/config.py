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

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Server
    PORT: int = 5002
    APP_ENV: str = "development"

    # Database
    DATABASE_URL: str

    # JWT
    ACCESS_TOKEN_SECRET: str
    ACCESS_TOKEN_EXPIRES_IN: str = "15m"
    ACCESS_TOKEN_MAX_AGE_MS: int = 15 * 60 * 1000  # 15 minutes

    REFRESH_TOKEN_SECRET: str
    REFRESH_TOKEN_EXPIRES_IN: str = "7d"
    REFRESH_TOKEN_MAX_AGE_MS: int = 7 * 24 * 60 * 60 * 1000  # 7 days

    # Redis / Queue
    REDIS_URL: str
    QUEUE_CONCURRENCY: int = 5

    # CORS
    CORS_ORIGIN: Optional[str] = None

    @field_validator("ACCESS_TOKEN_SECRET", "REFRESH_TOKEN_SECRET")
    @classmethod
    def validate_secret_length(cls, v: str, info) -> str:
        if len(v) < 16:
            raise ValueError(f"{info.field_name} must be at least 16 characters")
        return v

    @field_validator("APP_ENV")
    @classmethod
    def validate_env(cls, v: str) -> str:
        allowed = {"development", "production", "test"}
        if v not in allowed:
            raise ValueError(f"APP_ENV must be one of {allowed}")
        return v

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def is_development(self) -> bool:
        return self.APP_ENV == "development"

    # Convert "15m" / "7d" style strings to seconds for python-jose
    @property
    def access_token_expire_seconds(self) -> int:
        return _parse_duration(self.ACCESS_TOKEN_EXPIRES_IN)

    @property
    def refresh_token_expire_seconds(self) -> int:
        return _parse_duration(self.REFRESH_TOKEN_EXPIRES_IN)


def _parse_duration(value: str) -> int:
    """Parse '15m', '7d', '1h' duration strings to seconds."""
    unit = value[-1]
    amount = int(value[:-1])
    multipliers = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    if unit not in multipliers:
        raise ValueError(f"Unknown duration unit '{unit}' in '{value}'")
    return amount * multipliers[unit]


# ---------------------------------------------------------------------------
# Validate on import — exit immediately if required vars are missing / invalid
# (mirrors the process.exit(1) in env.ts)
# ---------------------------------------------------------------------------
try:
    settings = Settings()
except Exception as exc:
    print(f"❌ Invalid or missing environment variables:\n{exc}", file=sys.stderr)
    sys.exit(1)
