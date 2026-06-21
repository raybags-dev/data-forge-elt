"""Pydantic models for Kaggle ingestion."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field, model_validator


class KaggleDataset(BaseModel):
    """Represents a Kaggle dataset with metadata.

    Attributes:
        owner: Dataset owner's Kaggle username.
        name: Dataset slug name.
        full_name: Combined owner/name identifier (auto-computed if omitted).
        description: Optional human-readable description.
        size_bytes: Total download size in bytes.
        file_count: Number of files in the dataset.
        last_updated: Datetime of the last dataset update on Kaggle.
    """

    owner: str
    name: str
    full_name: str = Field(default="")
    description: str | None = None
    size_bytes: int | None = None
    file_count: int | None = None
    last_updated: datetime | None = None

    @model_validator(mode="after")
    def _set_full_name(self) -> KaggleDataset:
        """Auto-compute full_name from owner/name if not supplied."""
        if not self.full_name:
            self.full_name = f"{self.owner}/{self.name}"
        return self


class DownloadResult(BaseModel):
    """Result of a Kaggle dataset download operation.

    Attributes:
        dataset: The KaggleDataset that was downloaded.
        download_path: Local directory where files were saved.
        parquet_files: List of parquet files produced by the converter.
        rows_total: Total number of rows across all converted parquet files.
        success: Whether the download completed without error.
        error: Error message if the download failed.
        duration_seconds: Wall-clock time for the operation.
    """

    dataset: KaggleDataset
    download_path: Path
    parquet_files: list[Path]
    rows_total: int
    success: bool
    error: str | None = None
    duration_seconds: float
