"""Tests for shared.utils."""

from __future__ import annotations

from datetime import UTC
from pathlib import Path

import pytest

from shared.utils import (
    chunk_list,
    ensure_directory,
    flatten_dict,
    parse_size,
    safe_cast,
    slugify,
    timestamp_str,
    truncate_string,
    utc_now,
)


def test_ensure_directory_creates_nested_path(tmp_path: Path) -> None:
    """ensure_directory should create all parent directories."""
    target = tmp_path / "a" / "b" / "c"
    assert not target.exists()
    result = ensure_directory(target)
    assert target.exists()
    assert target.is_dir()
    assert result == target


def test_ensure_directory_idempotent(tmp_path: Path) -> None:
    """Calling ensure_directory twice on the same path should not raise."""
    target = tmp_path / "existing"
    ensure_directory(target)
    ensure_directory(target)  # must not raise
    assert target.exists()


def test_slugify_cleans_text() -> None:
    """slugify should produce lowercase underscore-separated identifiers."""
    assert slugify("Hello World!") == "hello_world"
    assert slugify("  My Data Source  ") == "my_data_source"
    assert slugify("CamelCase") == "camelcase"
    assert slugify("multiple   spaces") == "multiple_spaces"


def test_safe_cast_returns_default_on_failure() -> None:
    """safe_cast should return default when casting fails."""
    assert safe_cast("not_a_number", int, default=0) == 0
    assert safe_cast("3.14", float) == pytest.approx(3.14)
    assert safe_cast(None, int, default=-1) == -1


def test_chunk_list_yields_correct_sizes() -> None:
    """chunk_list should yield chunks of at most the specified size."""
    result = list(chunk_list([1, 2, 3, 4, 5], 2))
    assert result == [[1, 2], [3, 4], [5]]

    result_exact = list(chunk_list([1, 2, 3, 4], 2))
    assert result_exact == [[1, 2], [3, 4]]


def test_chunk_list_empty() -> None:
    """chunk_list with an empty list should yield nothing."""
    assert list(chunk_list([], 3)) == []


def test_truncate_string_truncates_long_strings() -> None:
    """Strings longer than max_len should end with ellipsis."""
    long = "a" * 300
    result = truncate_string(long, max_len=10)
    assert len(result) == 10
    assert result.endswith("...")


def test_truncate_string_short_strings_unchanged() -> None:
    """Strings shorter than max_len should be returned as-is."""
    short = "hello"
    assert truncate_string(short, max_len=200) == "hello"


def test_utc_now_is_timezone_aware() -> None:
    """utc_now() should return a timezone-aware datetime."""

    now = utc_now()
    assert now.tzinfo is not None
    assert now.tzinfo == UTC


def test_timestamp_str_no_colons() -> None:
    """timestamp_str() should not contain colons (safe for filenames)."""
    ts = timestamp_str()
    assert ":" not in ts


def test_flatten_dict() -> None:
    """flatten_dict should collapse nested dicts with dot-separated keys."""
    nested = {"a": {"b": 1, "c": {"d": 2}}}
    flat = flatten_dict(nested)
    assert flat == {"a.b": 1, "a.c.d": 2}


def test_parse_size_mb() -> None:
    """parse_size should convert MB strings to bytes."""
    assert parse_size("5 MB") == 5 * 1024 * 1024


def test_parse_size_kb() -> None:
    """parse_size should convert KB strings to bytes."""
    assert parse_size("1 KB") == 1024


def test_parse_size_invalid() -> None:
    """parse_size should raise ValueError for unrecognised strings."""
    with pytest.raises(ValueError):
        parse_size("not a size")
