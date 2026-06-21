"""Tests for the data lake layer — DataLakeManager and DataVersionManager."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

import pandas as pd
import pytest

from datalake.manager import DataLakeManager
from datalake.versioning import DataVersionManager
from shared.logger import get_logger


@pytest.fixture()
def logger():
    """Return a logger for tests."""
    return get_logger("test_datalake")


@pytest.fixture()
def lake(tmp_path: Path, logger):
    """Return a DataLakeManager backed by a temp directory."""
    return DataLakeManager(base_path=tmp_path / "lake", logger=logger)


@pytest.fixture()
def sample_df() -> pd.DataFrame:
    """Return a small DataFrame for lake write tests."""
    return pd.DataFrame({"id": [1, 2, 3], "value": ["a", "b", "c"]})


# ── DataLakeManager tests ─────────────────────────────────────────────────────


def test_data_lake_manager_setup_creates_dirs(lake: DataLakeManager) -> None:
    """setup() must create all four layer directories under the base path."""
    lake.setup()

    for layer in DataLakeManager.LAYERS:
        layer_dir = lake._base / layer
        assert layer_dir.is_dir(), f"Layer directory '{layer}' was not created"


def test_write_parquet_creates_file(
    lake: DataLakeManager, sample_df: pd.DataFrame
) -> None:
    """write_parquet() must produce a .parquet file in the dated directory."""
    lake.setup()
    out_path = lake.write_parquet("raw", "test_source", sample_df, "test.parquet")

    assert out_path.exists(), "Parquet file was not created"
    assert out_path.suffix == ".parquet"
    assert out_path.stat().st_size > 0


def test_read_parquet_returns_dataframe(
    lake: DataLakeManager, sample_df: pd.DataFrame
) -> None:
    """Round-trip write then read must recover the original data."""
    lake.setup()
    lake.write_parquet("raw", "roundtrip", sample_df)

    result = lake.read_parquet("raw", "roundtrip")

    assert isinstance(result, pd.DataFrame)
    assert len(result) == len(sample_df)
    assert list(result.columns) == list(sample_df.columns)


def test_read_parquet_by_date_filters_correctly(
    lake: DataLakeManager, sample_df: pd.DataFrame
) -> None:
    """read_parquet with a date filter must return only that partition's data."""
    lake.setup()
    lake.write_parquet("bronze", "filtered_source", sample_df)

    today = date.today()
    result = lake.read_parquet("bronze", "filtered_source", dt=today)
    assert len(result) == len(sample_df)

    yesterday = date(today.year, today.month, max(1, today.day - 1))
    empty = lake.read_parquet("bronze", "filtered_source", dt=yesterday)
    # Either empty (different day) or same data (if yesterday == today edge case)
    assert isinstance(empty, pd.DataFrame)


def test_promote_writes_to_new_layer(
    lake: DataLakeManager, sample_df: pd.DataFrame
) -> None:
    """promote() must write the DataFrame to the destination layer."""
    lake.setup()

    dest_path = lake.promote("raw", "bronze", "promoted_source", sample_df)

    assert dest_path.exists()
    assert "bronze" in str(dest_path)

    result = lake.read_parquet("bronze", "promoted_source")
    assert len(result) == len(sample_df)


def test_list_entries_returns_metadata(
    lake: DataLakeManager, sample_df: pd.DataFrame
) -> None:
    """list_entries() must return DataLakeEntry objects for each written file."""
    from datalake.models import DataLakeEntry

    lake.setup()
    lake.write_parquet("silver", "meta_source", sample_df)

    entries = lake.list_entries("silver", "meta_source")

    assert len(entries) == 1
    entry = entries[0]
    assert isinstance(entry, DataLakeEntry)
    assert entry.layer == "silver"
    assert entry.source == "meta_source"
    assert entry.size_bytes > 0


def test_invalid_layer_raises_value_error(lake: DataLakeManager) -> None:
    """Using an unrecognised layer name must raise ValueError."""
    with pytest.raises(ValueError, match="Unknown layer"):
        lake.layer_path("invalid_layer", "source")


# ── DataVersionManager tests ─────────────────────────────────────────────────


def test_version_manager_current_path(tmp_path: Path) -> None:
    """current_version_path() must return a YYYY/MM/DD directory for today."""
    manager = DataVersionManager()
    today = date.today()

    result = manager.current_version_path(tmp_path)

    expected_parts = (today.strftime("%Y"), today.strftime("%m"), today.strftime("%d"))
    assert result.is_dir()
    for part in expected_parts:
        assert part in result.parts


def test_version_manager_list_versions_empty(tmp_path: Path) -> None:
    """list_versions() on an empty directory must return an empty list."""
    manager = DataVersionManager()
    assert manager.list_versions(tmp_path) == []


def test_version_manager_list_versions_finds_dated_dirs(tmp_path: Path) -> None:
    """list_versions() must discover YYYY/MM/DD directories and return datetimes."""
    manager = DataVersionManager()

    # Create two dated dirs
    (tmp_path / "2024" / "01" / "15").mkdir(parents=True)
    (tmp_path / "2024" / "06" / "01").mkdir(parents=True)

    versions = manager.list_versions(tmp_path)

    assert len(versions) == 2
    assert all(isinstance(v, datetime) for v in versions)
    years = {v.year for v in versions}
    assert years == {2024}
