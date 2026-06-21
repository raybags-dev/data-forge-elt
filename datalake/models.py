"""Pydantic models for the data lake layer."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from pydantic import BaseModel


class DataLakeEntry(BaseModel):
    """Metadata record for a file stored in the data lake.

    Attributes:
        layer: Lake layer name (raw, bronze, silver, gold).
        source: Source identifier within the layer.
        path: Full filesystem path to the file.
        filename: Bare filename component.
        created_at: Datetime when the file was written.
        size_bytes: File size in bytes.
        row_count: Number of rows (None if not a tabular file).
    """

    layer: str
    source: str
    path: Path
    filename: str
    created_at: datetime
    size_bytes: int
    row_count: int | None = None


class LayerPath(BaseModel):
    """Represents a resolved layer/source path in the data lake.

    Attributes:
        layer: Lake layer name.
        source: Source identifier.
        base_path: Absolute path to the layer/source directory.
    """

    layer: str
    source: str
    base_path: Path
