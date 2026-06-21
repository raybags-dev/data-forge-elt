"""General-purpose utilities for DataForge ELT.

All functions are stateless and have no side effects beyond filesystem mutations
where explicitly documented.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


def ensure_directory(path: str | Path) -> Path:
    """Create *path* (and all parents) if it does not already exist.

    Args:
        path: Directory path to create.

    Returns:
        The resolved Path object.
    """
    resolved = Path(path)
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def utc_now() -> datetime:
    """Return the current UTC datetime with timezone information.

    Returns:
        Timezone-aware datetime in UTC.
    """
    return datetime.now(tz=timezone.utc)


def timestamp_str() -> str:
    """Return the current UTC time as an ISO-8601 string safe for filenames.

    Colons are replaced with hyphens so the string can be used as part of a
    file or directory name on all platforms.

    Returns:
        String like ``2024-05-01T12-30-00.123456+00-00``.
    """
    return utc_now().isoformat().replace(":", "-")


def slugify(text: str) -> str:
    """Convert *text* to a lowercase, underscore-separated identifier.

    Spaces and sequences of non-alphanumeric characters are replaced with a
    single underscore. Leading/trailing underscores are stripped.

    Args:
        text: Arbitrary string to normalise.

    Returns:
        URL/filename-safe slug string.

    Examples:
        >>> slugify("Hello World!")
        'hello_world'
        >>> slugify("  My Data Source  ")
        'my_data_source'
    """
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def safe_cast(value: Any, target_type: type, default: Any = None) -> Any:
    """Attempt to cast *value* to *target_type*, returning *default* on failure.

    Args:
        value: The value to cast.
        target_type: The type to cast to (e.g. ``int``, ``float``).
        default: Value returned when casting fails.

    Returns:
        The cast value, or *default* if an exception was raised.
    """
    try:
        return target_type(value)
    except (TypeError, ValueError):
        return default


def flatten_dict(d: dict, sep: str = ".") -> dict:
    """Flatten a nested dictionary into a single-level dict.

    Keys are joined with *sep*.

    Args:
        d: Dictionary to flatten (may be arbitrarily nested).
        sep: Separator inserted between key levels.

    Returns:
        Flat dictionary.

    Examples:
        >>> flatten_dict({"a": {"b": 1, "c": 2}})
        {'a.b': 1, 'a.c': 2}
    """

    def _flatten(obj: Any, prefix: str) -> dict:
        items: dict = {}
        if isinstance(obj, dict):
            for k, v in obj.items():
                new_key = f"{prefix}{sep}{k}" if prefix else str(k)
                items.update(_flatten(v, new_key))
        else:
            items[prefix] = obj
        return items

    return _flatten(d, "")


def chunk_list(items: list, size: int) -> Iterator[list]:
    """Yield successive non-overlapping chunks of *size* from *items*.

    Args:
        items: The list to chunk.
        size: Maximum number of elements per chunk.

    Yields:
        Sub-lists of at most *size* elements.

    Examples:
        >>> list(chunk_list([1, 2, 3, 4, 5], 2))
        [[1, 2], [3, 4], [5]]
    """
    for i in range(0, len(items), size):
        yield items[i : i + size]


def parse_size(size_str: str) -> int:
    """Parse a human-readable size string to an integer number of bytes.

    Supported suffixes (case-insensitive): B, KB, MB, GB, TB.

    Args:
        size_str: Size string such as ``"5 MB"`` or ``"1GB"``.

    Returns:
        Integer number of bytes.

    Raises:
        ValueError: If *size_str* cannot be parsed.

    Examples:
        >>> parse_size("5 MB")
        5242880
        >>> parse_size("1 KB")
        1024
    """
    units = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3, "TB": 1024**4}
    match = re.match(r"^\s*(\d+(?:\.\d+)?)\s*([a-zA-Z]*)\s*$", size_str.strip())
    if not match:
        raise ValueError(f"Cannot parse size string: {size_str!r}")
    number_str, unit = match.groups()
    unit = unit.upper() or "B"
    if unit not in units:
        raise ValueError(f"Unknown size unit {unit!r} in {size_str!r}")
    return int(float(number_str) * units[unit])


def truncate_string(s: str, max_len: int = 200) -> str:
    """Truncate *s* to at most *max_len* characters, appending ellipsis if cut.

    Args:
        s: String to potentially truncate.
        max_len: Maximum allowed length (including ellipsis).

    Returns:
        The original string, or a truncated version ending in ``...``.
    """
    if len(s) <= max_len:
        return s
    return s[: max_len - 3] + "..."
