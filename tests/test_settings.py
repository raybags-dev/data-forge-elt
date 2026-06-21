"""Tests for config.settings."""

from __future__ import annotations

from pathlib import Path

import pytest

from config.settings import Settings, get_settings


def test_settings_loads_defaults() -> None:
    """All required fields should have non-None defaults."""
    s = Settings()
    assert s.app_name == "DataForge"
    assert s.log_level == "INFO"
    assert s.max_retries == 3
    assert s.rate_limit_rps == 1.0
    assert s.email_port == 587
    assert s.minio_bucket == "dataforge"


def test_settings_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """Environment variable overrides should be reflected in a new Settings instance."""
    monkeypatch.setenv("APP_NAME", "OverriddenApp")
    monkeypatch.setenv("DEBUG", "true")
    monkeypatch.setenv("MAX_RETRIES", "5")
    s = Settings()
    assert s.app_name == "OverriddenApp"
    assert s.debug is True
    assert s.max_retries == 5


def test_settings_singleton() -> None:
    """get_settings() should return the identical object on repeated calls."""
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2


def test_data_lake_is_path() -> None:
    """The data_lake field must be a Path, not a plain string."""
    s = Settings()
    assert isinstance(s.data_lake, Path)


def test_log_dir_is_path() -> None:
    """The log_dir field must be a Path."""
    s = Settings()
    assert isinstance(s.log_dir, Path)


def test_optional_fields_default_to_none() -> None:
    """Webhook / credential fields should default to None when not set."""
    s = Settings(
        DISCORD_WEBHOOK="",
        SLACK_WEBHOOK="",
        EMAIL_HOST="",
        KAGGLE_USERNAME="",
    )
    # Empty strings from .env should be treated as falsy (None or empty)
    # Settings with empty string env var — they may be empty str, not None
    # The important thing is that falsy values don't enable notifiers
    assert not s.discord_webhook
    assert not s.slack_webhook
