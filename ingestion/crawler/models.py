"""Pydantic models for crawler ingestion."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel


class IngestionResult(BaseModel):
    """Result of a crawler data ingestion operation.

    Attributes:
        source: Name of the crawler source (e.g., "imdb", "reddit").
        layer: Data lake layer written to (e.g., "raw").
        files_ingested: Number of files successfully moved/written.
        rows_total: Total rows ingested across all files.
        output_path: Destination directory in the data lake.
        success: Whether the ingestion completed without error.
        error: Error message if ingestion failed.
    """

    source: str
    layer: str
    files_ingested: int
    rows_total: int
    output_path: Path
    success: bool
    error: str | None = None
