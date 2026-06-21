"""Request/response schemas for the crawl endpoint."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CrawlRequest(BaseModel):
    """Request body for POST /crawl.

    Attributes:
        source: Source identifier (e.g. "reddit", "imdb").
        urls: List of seed URLs to crawl.
        output_name: Optional override for the output filename stem.
    """

    source: str = Field(..., description="Source identifier (e.g. 'reddit', 'imdb')")
    urls: list[str] = Field(..., description="Seed URLs to crawl")
    output_name: str | None = Field(default=None, description="Optional output name override")


class CrawlResponse(BaseModel):
    """Response for a completed or queued crawl operation.

    Attributes:
        run_id: Unique identifier for this crawl job.
        status: Current status of the crawl operation.
        message: Human-readable result message.
        output_path: Filesystem path where output was saved, if available.
    """

    run_id: str
    status: str
    message: str
    output_path: str | None = None
