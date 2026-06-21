"""Unit tests for crawlers/base — models, rate limiter, robots, pagination."""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from crawlers.base.models import CrawledPage, CrawlResult, CrawlStatus, CrawlerProfile
from crawlers.base.pagination import CursorStrategy, NoPagination, PageNumberStrategy
from crawlers.base.rate_limit import RateLimiter
from crawlers.base.robots import RobotsChecker


# ── Helpers ───────────────────────────────────────────────────────────────────


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _make_page(url: str = "https://example.com", html: str = "") -> CrawledPage:
    return CrawledPage(
        url=url,
        status_code=200,
        html=html,
        text="",
        loaded_at=_utc_now(),
        response_time_ms=100,
    )


# ── RateLimiter tests ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_rate_limiter_wait_delays_appropriately() -> None:
    """RateLimiter should delay approximately 1/rps seconds when bucket is empty."""
    limiter = RateLimiter(requests_per_second=2.0)
    # Drain the bucket
    for _ in range(4):
        await limiter.wait()

    t_start = time.monotonic()
    await limiter.wait()
    elapsed = time.monotonic() - t_start

    # At 2 rps, a delay of at least ~0.3s expected when empty; use loose bound
    assert elapsed >= 0.3, f"Expected delay ≥ 0.3s, got {elapsed:.3f}s"


@pytest.mark.asyncio
async def test_rate_limiter_respects_rps() -> None:
    """RateLimiter should allow rapid successive calls within the token budget."""
    limiter = RateLimiter(requests_per_second=10.0)
    # The bucket starts full (capacity = 20), so the first 20 calls are instant
    t_start = time.monotonic()
    for _ in range(10):
        await limiter.wait()
    elapsed = time.monotonic() - t_start
    # 10 calls against a 20-token bucket should complete in well under 1 s
    assert elapsed < 1.0, f"Expected fast completion, took {elapsed:.3f}s"


@pytest.mark.asyncio
async def test_rate_limiter_property() -> None:
    """requests_per_second property should reflect the constructor value."""
    limiter = RateLimiter(requests_per_second=3.5)
    assert limiter.requests_per_second == 3.5


# ── RobotsChecker tests ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_robots_checker_disabled_allows_all() -> None:
    """Disabled RobotsChecker must allow every URL without making network calls."""
    checker = RobotsChecker(enabled=False)
    assert await checker.is_allowed("https://example.com/secret") is True
    assert await checker.is_allowed("https://evil.com/private") is True


@pytest.mark.asyncio
async def test_robots_checker_fails_open() -> None:
    """On network error fetching robots.txt, checker should allow the URL."""
    from unittest.mock import AsyncMock

    checker = RobotsChecker(enabled=True)
    # Patch the AsyncClient so its __aenter__ returns a mock whose .get raises
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=Exception("network error"))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await checker.is_allowed("https://example.com/page")
    assert result is True


# ── CrawlerProfile tests ──────────────────────────────────────────────────────


def test_crawler_profile_defaults() -> None:
    """CrawlerProfile must expose all expected fields with sensible defaults."""
    profile = CrawlerProfile(name="test", base_url="https://example.com")
    assert profile.name == "test"
    assert profile.base_url == "https://example.com"
    assert isinstance(profile.timeout, int)
    assert isinstance(profile.headless, bool)
    assert isinstance(profile.max_retries, int)
    assert isinstance(profile.rate_limit_rps, float)
    assert isinstance(profile.robots_txt_compliance, bool)
    assert isinstance(profile.screenshot_on_failure, bool)
    assert isinstance(profile.cookies, dict)
    assert isinstance(profile.headers, dict)
    assert profile.proxy is None
    assert isinstance(profile.user_agent, str)
    assert len(profile.user_agent) > 0


def test_crawler_profile_custom_values() -> None:
    """CrawlerProfile should store custom values correctly."""
    profile = CrawlerProfile(
        name="custom",
        base_url="https://test.com",
        timeout=60,
        headless=False,
        rate_limit_rps=2.5,
        proxy="http://proxy:8080",
        cookies={"session": "abc"},
    )
    assert profile.timeout == 60
    assert profile.headless is False
    assert profile.rate_limit_rps == 2.5
    assert profile.proxy == "http://proxy:8080"
    assert profile.cookies == {"session": "abc"}


# ── CrawlResult tests ─────────────────────────────────────────────────────────


def test_crawl_result_duration() -> None:
    """CrawlResult.duration_seconds should compute elapsed seconds correctly."""
    from datetime import timedelta

    started = _utc_now()
    ended = started + timedelta(seconds=42)
    result = CrawlResult(
        profile_name="test",
        status=CrawlStatus.SUCCESS,
        started_at=started,
        ended_at=ended,
    )
    assert result.duration_seconds == pytest.approx(42.0, abs=0.01)


def test_crawl_result_duration_running() -> None:
    """CrawlResult.duration_seconds returns None when crawl is still running."""
    result = CrawlResult(
        profile_name="test",
        status=CrawlStatus.RUNNING,
        started_at=_utc_now(),
        ended_at=None,
    )
    assert result.duration_seconds is None


def test_crawl_result_default_fields() -> None:
    """CrawlResult should initialise list fields to empty collections."""
    result = CrawlResult(
        profile_name="test",
        status=CrawlStatus.PENDING,
        started_at=_utc_now(),
    )
    assert result.pages_fetched == 0
    assert result.records_extracted == 0
    assert result.errors == []
    assert result.output_path is None


def test_crawl_status_values() -> None:
    """CrawlStatus enum should contain all required statuses."""
    statuses = {s.value for s in CrawlStatus}
    assert statuses == {"PENDING", "RUNNING", "SUCCESS", "FAILED", "RATE_LIMITED", "SKIPPED"}


# ── CrawledPage tests ─────────────────────────────────────────────────────────


def test_crawled_page_fields() -> None:
    """CrawledPage should store all fields correctly."""
    now = _utc_now()
    page = CrawledPage(
        url="https://example.com",
        status_code=200,
        html="<html></html>",
        text="Hello",
        title="Test",
        headers={"content-type": "text/html"},
        loaded_at=now,
        response_time_ms=250,
    )
    assert page.url == "https://example.com"
    assert page.status_code == 200
    assert page.title == "Test"
    assert page.response_time_ms == 250


# ── Pagination tests ──────────────────────────────────────────────────────────


def test_pagination_no_pagination_returns_none() -> None:
    """NoPagination.next_url must always return None."""
    strategy = NoPagination()
    for page_num in range(1, 5):
        assert strategy.next_url("https://example.com", "<html/>", page_num) is None


def test_page_number_strategy_increments() -> None:
    """PageNumberStrategy should build correct next-page URLs."""
    strategy = PageNumberStrategy(max_pages=5)
    url = "https://example.com/listing"
    next_url = strategy.next_url(url, "", 1)
    assert next_url is not None
    assert "page=2" in next_url


def test_page_number_strategy_stops_at_max() -> None:
    """PageNumberStrategy returns None when current_page == max_pages."""
    strategy = PageNumberStrategy(max_pages=3)
    result = strategy.next_url("https://example.com", "", 3)
    assert result is None


def test_page_number_strategy_preserves_existing_params() -> None:
    """PageNumberStrategy should keep existing query params."""
    strategy = PageNumberStrategy(max_pages=10)
    url = "https://example.com/search?q=python&sort=new"
    next_url = strategy.next_url(url, "", 1)
    assert next_url is not None
    assert "q=python" in next_url
    assert "page=2" in next_url


def test_cursor_strategy_no_element_returns_none() -> None:
    """CursorStrategy returns None when the CSS selector matches nothing."""
    strategy = CursorStrategy(cursor_selector=".next-cursor")
    result = strategy.next_url("https://example.com", "<html><body></body></html>", 1)
    assert result is None
