"""Request/response schemas for the datasets endpoint."""

from __future__ import annotations

from pydantic import BaseModel, Field


class DatasetItem(BaseModel):
    """Metadata for a single Parquet dataset in the lake.

    Attributes:
        source: Data source identifier.
        layer: Lake layer (raw, bronze, silver, gold).
        name: Dataset filename stem.
        path: Absolute filesystem path.
        size_bytes: File size in bytes.
        created_at: ISO-8601 creation timestamp.
    """

    source: str
    layer: str
    name: str
    path: str
    size_bytes: int
    created_at: str


class DatasetListResponse(BaseModel):
    """Response for GET /datasets.

    Attributes:
        datasets: List of available dataset items.
        total: Total count of discovered datasets.
    """

    datasets: list[DatasetItem] = Field(default_factory=list)
    total: int = 0
