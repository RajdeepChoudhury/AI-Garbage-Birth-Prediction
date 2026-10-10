"""Application settings, loaded from environment variables or a .env file."""
from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]
logger = logging.getLogger(__name__)
DEFAULT_SECRET = "change-me-in-production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"
    database_url: str = "sqlite:///./garbage.db"
    secret_key: str = DEFAULT_SECRET
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 30
    refresh_token_days: int = 7
    ml_dir: Path = ROOT / "ml"
    admin_email: str | None = None  # first admin, created at startup when both are set
    admin_password: str | None = None
    # Volume above which a ward is treated as overflowing (80th percentile of the
    # synthetic training data). Replace with real bin capacity per ward later.
    overflow_capacity: float = 2.9
    rate_limit_default: str = "120/minute"
    redis_url: str | None = None  # shared rate limit storage for multiple workers
    rate_limit_login: str = "10/minute"
    max_upload_bytes: int = 10 * 1024 * 1024
    rate_limit_assistant: str = "20/minute"
    # Groq assistant. Models are retired often, so check console.groq.com/docs/deprecations.
    groq_api_key: str | None = None
    groq_model: str = "openai/gpt-oss-120b"
    # Sent only to gpt-oss models. Low keeps reasoning short so answers are not cut off.
    groq_reasoning_effort: str | None = "low"
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_timeout: float = 30.0
    groq_max_tokens: int = 2048  # includes reasoning tokens for gpt-oss models
    groq_temperature: float = 0.2
    cors_origins: list[str] = ["http://localhost:5173"]

    @field_validator("database_url")
    @classmethod
    def use_psycopg2_driver(cls, value: str) -> str:
        """Render gives plain postgresql:// URLs. Newer SQLAlchemy would then look for
        psycopg (version 3), which is not installed, so name psycopg2 explicitly."""
        for prefix in ("postgres://", "postgresql://"):
            if value.startswith(prefix):
                return "postgresql+psycopg2://" + value[len(prefix):]
        return value


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    if s.secret_key == DEFAULT_SECRET:
        if s.environment == "production":
            raise RuntimeError("SECRET_KEY must be set in production")
        logger.warning("Using the default SECRET_KEY. Set SECRET_KEY before deploying.")
    return s
