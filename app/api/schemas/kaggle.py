"""Request/response schemas for the Kaggle endpoint."""

from __future__ import annotations

from pydantic import BaseModel, Field


class KaggleDownloadRequest(BaseModel):
    """Request body for POST /kaggle/download.

    Attributes:
        dataset: Kaggle dataset slug in "owner/name" format.
        force: Re-download even if files already exist locally.
    """

    dataset: str = Field(
        ...,
        description="Kaggle dataset slug in 'owner/name' format",
        examples=["zillow/zecon"],
    )
    force: bool = Field(default=False, description="Re-download even if already cached")


class KaggleDownloadResponse(BaseModel):
    """Response for a completed Kaggle download.

    Attributes:
        dataset_name: The dataset slug that was downloaded.
        parquet_files: List of local parquet file paths produced.
        rows_total: Total rows across all parquet files.
        duration_seconds: Wall-clock time for the operation.
        success: Whether the download completed without error.
    """

    dataset_name: str
    parquet_files: list[str]
    rows_total: int
    duration_seconds: float
    success: bool
