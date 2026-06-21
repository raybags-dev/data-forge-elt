"""Shared pytest fixtures for DataForge ELT tests."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from shared.notifier import NotificationPayload, Notifier

if TYPE_CHECKING:
    pass


class _MockNotifier(Notifier):
    """Test double that records every payload sent to it."""

    def __init__(self) -> None:
        self.calls: list[NotificationPayload] = []

    def send(self, payload: NotificationPayload) -> None:
        self.calls.append(payload)


@pytest.fixture()
def mock_notifier() -> _MockNotifier:
    """Return a Notifier that records calls instead of delivering them."""
    return _MockNotifier()


@pytest.fixture()
def tmp_settings(tmp_path: Path):
    """Return a Settings instance with all path fields pointing to tmp_path.

    The lru_cache on get_settings() is bypassed by constructing Settings
    directly with environment-variable overrides.
    """
    from config.settings import Settings

    return Settings(
        APP_NAME="TestForge",
        DEBUG=True,
        LOG_LEVEL="DEBUG",
        LOG_DIR=str(tmp_path / "logs"),
        LOG_ROTATION="1 MB",
        LOG_RETENTION="1 days",
        DATA_LAKE=str(tmp_path / "datalake"),
        DUCKDB_PATH=str(tmp_path / "warehouse" / "test.duckdb"),
        DBT_PROJECT_DIR=str(tmp_path / "dbt"),
        DBT_PROFILES_DIR=str(tmp_path / "dbt"),
        MINIO_ENDPOINT="http://localhost:9000",
        MINIO_ACCESS_KEY="minioadmin",
        MINIO_SECRET_KEY="minioadmin",
        MINIO_BUCKET="test-bucket",
    )
