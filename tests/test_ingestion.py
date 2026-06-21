"""Tests for the ingestion layer — CsvToParquetConverter and KaggleDownloader."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
import pytest

from ingestion.kaggle.converter import CsvToParquetConverter
from ingestion.kaggle.downloader import KaggleDownloader
from ingestion.kaggle.models import DownloadResult, KaggleDataset
from shared.exceptions import ConfigError
from shared.logger import get_logger
from shared.notifier import NotificationPayload, Notifier


class _MockNotifier(Notifier):
    """Records all sent payloads for assertion."""

    def __init__(self) -> None:
        self.calls: list[NotificationPayload] = []

    def send(self, payload: NotificationPayload) -> None:
        self.calls.append(payload)


@pytest.fixture()
def logger():
    """Return a test logger."""
    return get_logger("test_ingestion")


@pytest.fixture()
def converter(logger):
    """Return a CsvToParquetConverter for tests."""
    return CsvToParquetConverter(logger=logger)


@pytest.fixture()
def mock_notifier():
    """Return a mock notifier."""
    return _MockNotifier()


# ── CsvToParquetConverter tests ───────────────────────────────────────────────


def test_csv_to_parquet_converter(
    converter: CsvToParquetConverter, tmp_path: Path
) -> None:
    """CsvToParquetConverter must convert a CSV file to Parquet."""
    csv_path = tmp_path / "sample.csv"
    csv_path.write_text("id,name,value\n1,Alice,100\n2,Bob,200\n3,Charlie,300\n")

    parquet_path = converter.convert(csv_path)

    assert parquet_path.exists(), "Parquet file was not created"
    assert parquet_path.suffix == ".parquet"

    df = pd.read_parquet(parquet_path)
    assert len(df) == 3
    assert list(df.columns) == ["id", "name", "value"]


def test_csv_to_parquet_custom_output_path(
    converter: CsvToParquetConverter, tmp_path: Path
) -> None:
    """convert() must respect a custom output_path."""
    csv_path = tmp_path / "data.csv"
    csv_path.write_text("x,y\n1,2\n3,4\n")

    out = tmp_path / "subdir" / "output.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    result = converter.convert(csv_path, output_path=out)

    assert result == out
    assert out.exists()


def test_convert_all_csvs(
    converter: CsvToParquetConverter, tmp_path: Path
) -> None:
    """convert_all_csvs() must convert every CSV in a directory."""
    for i in range(3):
        (tmp_path / f"file_{i}.csv").write_text(f"col\nval{i}\n")

    results = converter.convert_all_csvs(tmp_path)

    assert len(results) == 3
    for p in results:
        assert p.exists()
        assert p.suffix == ".parquet"


def test_convert_all_csvs_empty_dir(
    converter: CsvToParquetConverter, tmp_path: Path
) -> None:
    """convert_all_csvs() on an empty directory must return an empty list."""
    results = converter.convert_all_csvs(tmp_path)
    assert results == []


def test_csv_to_parquet_handles_encoding(
    converter: CsvToParquetConverter, tmp_path: Path
) -> None:
    """convert() must handle latin-1 encoded CSV without crashing."""
    csv_path = tmp_path / "latin.csv"
    # Write a CSV with latin-1 characters
    csv_path.write_bytes("id,city\n1,M\xfcnchen\n2,K\xf6ln\n".encode("latin-1"))

    parquet_path = converter.convert(csv_path)

    assert parquet_path.exists()
    df = pd.read_parquet(parquet_path)
    assert len(df) == 2


# ── KaggleDownloader tests ────────────────────────────────────────────────────


def test_kaggle_downloader_requires_credentials(
    tmp_path: Path, mock_notifier: _MockNotifier, logger
) -> None:
    """KaggleDownloader must raise ConfigError if no Kaggle credentials are set."""
    from config.settings import Settings

    settings = Settings(
        DATA_LAKE=str(tmp_path / "lake"),
        DUCKDB_PATH=str(tmp_path / "db.duckdb"),
        LOG_DIR=str(tmp_path / "logs"),
        # Explicitly no kaggle credentials
        KAGGLE_USERNAME=None,
        KAGGLE_KEY=None,
    )

    downloader = KaggleDownloader(
        settings=settings,
        notifier=mock_notifier,
        logger=logger,
    )

    with pytest.raises(ConfigError, match="Kaggle credentials"):
        downloader._setup_kaggle_auth()


def test_kaggle_downloader_download_returns_failure_on_api_error(
    tmp_path: Path, mock_notifier: _MockNotifier, logger
) -> None:
    """download() must return DownloadResult with success=False when API fails."""
    from config.settings import Settings

    settings = Settings(
        DATA_LAKE=str(tmp_path / "lake"),
        DUCKDB_PATH=str(tmp_path / "db.duckdb"),
        LOG_DIR=str(tmp_path / "logs"),
        KAGGLE_USERNAME="test_user",
        KAGGLE_KEY="test_key",
    )

    downloader = KaggleDownloader(
        settings=settings,
        notifier=mock_notifier,
        logger=logger,
    )

    dataset = KaggleDataset(owner="owner", name="dataset")

    # Mock _get_api to return a fake API that raises on download
    fake_api = MagicMock()
    fake_api.dataset_download_files.side_effect = RuntimeError("API error")
    downloader._api = fake_api

    result = downloader.download(dataset)

    assert isinstance(result, DownloadResult)
    assert result.success is False
    assert result.error is not None
    assert len(mock_notifier.calls) == 1


def test_kaggle_dataset_full_name_auto_computed() -> None:
    """KaggleDataset.full_name must be auto-set from owner/name."""
    ds = KaggleDataset(owner="myuser", name="mydataset")
    assert ds.full_name == "myuser/mydataset"


def test_kaggle_dataset_explicit_full_name() -> None:
    """KaggleDataset.full_name must not be overridden if explicitly provided."""
    ds = KaggleDataset(owner="a", name="b", full_name="custom/name")
    assert ds.full_name == "custom/name"
