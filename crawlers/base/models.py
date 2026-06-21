"""Core data models for the DataForge crawler engine.

All models use Pydantic v2 for validation and serialisation.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class CrawlStatus(StrEnum):
    """Lifecycle state of a crawl operation."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    RATE_LIMITED = "RATE_LIMITED"
    SKIPPED = "SKIPPED"


class CrawlerProfile(BaseModel):
    """Configuration profile for a single crawler instance.

    Attributes:
        name: Human-readable identifier for this crawler.
        base_url: Root URL this crawler targets.
        timeout: Per-request timeout in seconds.
        headless: Whether to run the browser in headless mode.
        max_retries: Maximum retry attempts per URL.
        rate_limit_rps: Requests per second allowed by the rate limiter.
        robots_txt_compliance: Honour robots.txt restrictions when True.
        screenshot_on_failure: Capture a screenshot on fetch failure when True.
        cookies: Optional pre-seeded cookies to send with every request.
        headers: Extra HTTP headers to merge into each request.
        proxy: Optional proxy URL (e.g. ``http://user:pass@host:port``).
        user_agent: User-Agent header value.
    """

    name: str
    base_url: str
    timeout: int = 30
    headless: bool = True
    max_retries: int = 3
    rate_limit_rps: float = 1.0
    robots_txt_compliance: bool = True
    screenshot_on_failure: bool = True
    cookies: dict[str, str] = Field(default_factory=dict)
    headers: dict[str, str] = Field(default_factory=dict)
    proxy: str | None = None
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )


class CrawledPage(BaseModel):
    """Snapshot of a single fetched web page.

    Attributes:
        url: Final URL after redirects.
        status_code: HTTP response status code.
        html: Raw HTML body.
        text: Plain-text extracted from the page.
        title: ``<title>`` tag content, if present.
        headers: Response headers.
        loaded_at: UTC timestamp when the page finished loading.
        response_time_ms: Round-trip time in milliseconds.
    """

    url: str
    status_code: int
    html: str
    text: str
    title: str | None = None
    headers: dict[str, Any] = Field(default_factory=dict)
    loaded_at: datetime
    response_time_ms: int


class CrawlResult(BaseModel):
    """Summary produced after a crawl session completes.

    Attributes:
        profile_name: Name of the :class:`CrawlerProfile` used.
        pages_fetched: Number of pages successfully fetched.
        records_extracted: Total records extracted across all pages.
        status: Final crawl status.
        started_at: UTC timestamp when the crawl began.
        ended_at: UTC timestamp when the crawl finished (``None`` if still running).
        errors: List of error message strings accumulated during the run.
        output_path: Filesystem path where extracted records were saved.
    """

    profile_name: str
    pages_fetched: int = 0
    records_extracted: int = 0
    status: CrawlStatus = CrawlStatus.PENDING
    started_at: datetime
    ended_at: datetime | None = None
    errors: list[str] = Field(default_factory=list)
    output_path: str | None = None

    @property
    def duration_seconds(self) -> float | None:
        """Elapsed wall-clock time in seconds, or ``None`` if still running."""
        if self.ended_at is None:
            return None
        delta = self.ended_at - self.started_at
        return delta.total_seconds()
