"""Production Pydantic Settings for DataForge ELT."""

from __future__ import annotations

import functools
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application-wide configuration loaded from environment variables and .env file.

    All fields map 1-to-1 with environment variable names defined in .env.
    Use get_settings() to obtain the cached singleton.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────────────────
    app_name: str = Field(default="DataForge", alias="APP_NAME")
    debug: bool = Field(default=False, alias="DEBUG")

    # ── Logging ───────────────────────────────────────────────────────────────
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_dir: Path = Field(default=Path("./logs"), alias="LOG_DIR")
    log_rotation: str = Field(default="5 MB", alias="LOG_ROTATION")
    log_retention: str = Field(default="10 days", alias="LOG_RETENTION")

    # ── Storage paths ─────────────────────────────────────────────────────────
    data_lake: Path = Field(default=Path("./datalake"), alias="DATA_LAKE")
    duckdb_path: Path = Field(default=Path("./warehouse/data.duckdb"), alias="DUCKDB_PATH")
    dbt_project_dir: Path = Field(default=Path("./dbt"), alias="DBT_PROJECT_DIR")
    dbt_profiles_dir: Path = Field(default=Path("./dbt"), alias="DBT_PROFILES_DIR")

    # ── Crawler ───────────────────────────────────────────────────────────────
    crawler_timeout: int = Field(default=30, alias="CRAWLER_TIMEOUT")
    headless: bool = Field(default=True, alias="HEADLESS")
    max_retries: int = Field(default=3, alias="MAX_RETRIES")
    retry_wait_min: float = Field(default=1.0, alias="RETRY_WAIT_MIN")
    retry_wait_max: float = Field(default=30.0, alias="RETRY_WAIT_MAX")
    rate_limit_rps: float = Field(default=1.0, alias="RATE_LIMIT_RPS")
    robots_txt_compliance: bool = Field(default=True, alias="ROBOTS_TXT_COMPLIANCE")
    screenshot_on_failure: bool = Field(default=True, alias="SCREENSHOT_ON_FAILURE")
    screenshots_dir: Path = Field(
        default=Path("./logs/screenshots"), alias="SCREENSHOTS_DIR"
    )

    # ── Notifications ─────────────────────────────────────────────────────────
    discord_webhook: str | None = Field(default=None, alias="DISCORD_WEBHOOK")
    slack_webhook: str | None = Field(default=None, alias="SLACK_WEBHOOK")

    # ── Email ─────────────────────────────────────────────────────────────────
    email_host: str | None = Field(default=None, alias="EMAIL_HOST")
    email_port: int = Field(default=587, alias="EMAIL_PORT")
    email_user: str | None = Field(default=None, alias="EMAIL_USER")
    email_password: str | None = Field(default=None, alias="EMAIL_PASSWORD")
    email_from: str = Field(default="dataforge@localhost", alias="EMAIL_FROM")
    email_to: str | None = Field(default=None, alias="EMAIL_TO")

    # ── Kaggle ────────────────────────────────────────────────────────────────
    kaggle_username: str | None = Field(default=None, alias="KAGGLE_USERNAME")
    kaggle_key: str | None = Field(default=None, alias="KAGGLE_KEY")

    # ── AWS S3 ───────────────────────────────────────────────────────────────
    aws_access_key_id: str | None = Field(default=None, alias="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: str | None = Field(default=None, alias="AWS_SECRET_ACCESS_KEY")
    aws_region: str = Field(default="eu-central-1", alias="AWS_REGION")
    aws_s3_bucket: str = Field(default="dataforge-elt-storage", alias="AWS_S3_BUCKET")

    # ── MinIO (local dev S3-compatible) ───────────────────────────────────────
    minio_endpoint: str = Field(default="http://localhost:9000", alias="MINIO_ENDPOINT")
    minio_access_key: str = Field(default="minioadmin", alias="MINIO_ACCESS_KEY")
    minio_secret_key: str = Field(default="minioadmin", alias="MINIO_SECRET_KEY")
    minio_bucket: str = Field(default="dataforge", alias="MINIO_BUCKET")

    # ── Supabase ─────────────────────────────────────────────────────────────
    supabase_url: str | None = Field(default=None, alias="SUPABASE_URL")
    supabase_service_key: str | None = Field(default=None, alias="SUPABASE_SERVICE_KEY")
    supabase_bucket: str = Field(default="dataforge-elt-bucket", alias="SUPABASE_BUCKET")

    # ── portfolio-base service-to-service ─────────────────────────────────────
    portfolio_api_url: str | None = Field(default=None, alias="PORTFOLIO_API_URL")
    portfolio_admin_token: str | None = Field(default=None, alias="PORTFOLIO_ADMIN_TOKEN")

    # ── PostgreSQL (Supabase) ─────────────────────────────────────────────────
    database_url: str | None = Field(default=None, alias="DATABASE_URL")

    # ── MongoDB ───────────────────────────────────────────────────────────────
    mongodb_url: str | None = Field(default=None, alias="MONGODB_URL")
    mongodb_db: str = Field(default="dataforge_elt", alias="MONGODB_DB")

    # ── Security ──────────────────────────────────────────────────────────────
    secret_key: str = Field(
        default="change-me-in-production", alias="SECRET_KEY"
    )
    access_token_expire_minutes: int = Field(
        default=720, alias="ACCESS_TOKEN_EXPIRE_MINUTES"
    )

    # ── LLM / AI ──────────────────────────────────────────────────────────────
    groq_api_key: str | None = Field(default=None, alias="GROQ_API_KEY")
    ollama_url: str = Field(default="http://localhost:11434", alias="OLLAMA_URL")
    ollama_model: str = Field(default="llama3.2:3b", alias="OLLAMA_MODEL")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )


@functools.lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached singleton Settings instance.

    Uses lru_cache so the .env file is only parsed once per process.
    """
    return Settings()
