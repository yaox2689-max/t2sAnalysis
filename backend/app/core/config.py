"""App configuration via Pydantic Settings.

All configuration values are loaded from environment variables
or .env file. Every new config option should be added here with
a proper type annotation and description.
"""

import logging
from typing import Any

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

_DEV_SECRET = "dev-secret-do-not-use-in-prod"


class Settings(BaseSettings):
    """Application settings loaded from environment/.env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ──────────────────────────────────────────────
    APP_NAME: str = "AI Data Analyst"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # ── Server ───────────────────────────────────────────
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # ── CORS ─────────────────────────────────────────────
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]

    # ── Database (MySQL) ─────────────────────────────────
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = ""
    DB_NAME: str = "t2s_analysis"
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800

    # ── LLM ──────────────────────────────────────────────
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "deepseek-v4-pro"
    LLM_BASE_URL: str = "https://api.deepseek.com"

    # ── SQL Executor ─────────────────────────────────────
    SQL_TIMEOUT: int = 10
    SQL_MAX_ROWS: int = 500

    # ── Auth ────────────────────────────────────────────
    JWT_SECRET_KEY: str = _DEV_SECRET
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440

    # ── Rate Limiting ──────────────────────────────────
    RATE_LIMIT_DEFAULT: str = "60/minute"
    RATE_LIMIT_AUTH: str = "10/minute"
    RATE_LIMIT_CHAT: str = "5/minute"

    # ── Redis (cache) ──────────────────────────────────
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    # ── LangSmith Tracing（可选）────────────────────────
    # 填写 API Key 即启用，留空则不接入
    LANGSMITH_API_KEY: str = ""
    LANGSMITH_PROJECT: str = "t2s-analysis"

    def model_post_init(self, __context: Any) -> None:
        if self.JWT_SECRET_KEY == _DEV_SECRET:
            logger.warning(
                "JWT_SECRET_KEY is using the default development value. "
                "Set a strong random string in production via JWT_SECRET_KEY env var."
            )


settings = Settings()
