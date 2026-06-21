"""Abstract base crawler for the DataForge crawler engine.

All concrete crawlers inherit :class:`BaseCrawler` and implement the three
abstract methods: :meth:`fetch`, :meth:`parse`, and :meth:`validate`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pandas as pd

from shared.logger import get_logger
from shared.utils import ensure_directory, slugify, timestamp_str

if TYPE_CHECKING:
    from loguru import Logger

    from crawlers.base.browser import BrowserManager
    from crawlers.base.models import CrawledPage, CrawlerProfile, CrawlResult
    from crawlers.base.rate_limit import RateLimiter
    from shared.notifier import Notifier

_log = get_logger(__name__)


class BaseCrawler(ABC):
    """Abstract base for all DataForge crawlers.

    Subclasses must implement :meth:`fetch`, :meth:`parse`, and
    :meth:`validate`.  The orchestration is handled by :meth:`crawl` which
    calls these methods in order for each URL.

    Args:
        profile: Configuration profile for this crawler instance.
        browser_manager: Manages the Playwright browser lifecycle.
        rate_limiter: Enforces per-request rate limiting.
        notifier: Sends pipeline notifications.
        logger: Loguru logger bound to the concrete module.
    """

    def __init__(
        self,
        profile: CrawlerProfile,
        browser_manager: BrowserManager,
        rate_limiter: RateLimiter,
        notifier: Notifier,
        logger: Logger,
    ) -> None:
        self.profile = profile
        self._browser = browser_manager
        self._rate_limiter = rate_limiter
        self._notifier = notifier
        self._log = logger

    # ── Abstract interface ────────────────────────────────────────────────────

    @abstractmethod
    async def fetch(self, url: str) -> CrawledPage:
        """Fetch *url* and return a :class:`CrawledPage`.

        Args:
            url: The page URL to load.
        """

    @abstractmethod
    def parse(self, page: CrawledPage) -> list[dict[str, Any]]:
        """Extract raw records from *page*.

        Args:
            page: The fetched page snapshot.

        Returns:
            A list of dictionaries, one per extracted record.
        """

    @abstractmethod
    def validate(self, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Filter *records* to only those that pass validation.

        Args:
            records: Raw records returned by :meth:`parse`.

        Returns:
            Subset of *records* that passed all validation checks.
        """

    # ── Concrete helpers ──────────────────────────────────────────────────────

    def start(self) -> CrawlResult:
        """Create and return an initial :class:`CrawlResult` in RUNNING state."""
        from crawlers.base.models import CrawlResult, CrawlStatus

        self._log.info("Starting crawler '{name}'", name=self.profile.name)
        return CrawlResult(
            profile_name=self.profile.name,
            status=CrawlStatus.RUNNING,
            started_at=datetime.now(tz=UTC),
        )

    def clean(self, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Strip leading/trailing whitespace from all string values in *records*.

        Args:
            records: Records to sanitise in-place.

        Returns:
            The same list with string values stripped.
        """
        cleaned: list[dict[str, Any]] = []
        for record in records:
            cleaned.append(
                {
                    k: v.strip() if isinstance(v, str) else v
                    for k, v in record.items()
                }
            )
        return cleaned

    def save(self, records: list[dict[str, Any]], output_path: Path) -> int:
        """Persist *records* to a Parquet file at *output_path*.

        Creates parent directories if they do not exist.

        Args:
            records: Dicts to serialise.
            output_path: Destination ``.parquet`` file path.

        Returns:
            Number of rows written.
        """
        ensure_directory(output_path.parent)
        df = pd.DataFrame(records)
        df.to_parquet(output_path, index=False)
        self._log.info(
            "Saved {n} records to {path}", n=len(df), path=output_path
        )
        return len(df)

    def finish(self, result: CrawlResult) -> CrawlResult:
        """Mark *result* as finished, stop the browser, and send a notification.

        Args:
            result: The in-progress :class:`CrawlResult` to finalise.

        Returns:
            Updated result with ``ended_at`` set and final status.
        """
        from crawlers.base.models import CrawlStatus
        from shared.notifier import NotificationLevel, NotificationPayload

        result.ended_at = datetime.now(tz=UTC)
        if result.status == CrawlStatus.RUNNING:
            result.status = CrawlStatus.SUCCESS if not result.errors else CrawlStatus.FAILED

        self._log.info(
            "Crawler '{name}' finished | status={status} | pages={pages} | records={records} | duration={dur:.1f}s",
            name=self.profile.name,
            status=result.status.value,
            pages=result.pages_fetched,
            records=result.records_extracted,
            dur=result.duration_seconds or 0.0,
        )

        level = (
            NotificationLevel.INFO
            if result.status == CrawlStatus.SUCCESS
            else NotificationLevel.ERROR
        )
        payload = NotificationPayload(
            title=f"Crawler '{self.profile.name}' {result.status.value}",
            message=(
                f"Pages fetched: {result.pages_fetched} | "
                f"Records: {result.records_extracted} | "
                f"Errors: {len(result.errors)}"
            ),
            level=level,
        )
        try:
            self._notifier.send(payload)
        except Exception as exc:
            self._log.warning("Notification failed: {exc}", exc=exc)

        return result

    async def _take_screenshot(self, url: str) -> None:
        """Capture a screenshot of the current browser state.

        File is saved to ``settings.screenshots_dir / <timestamp>_<slug>.png``.

        Args:
            url: URL being captured (used to build the filename slug).
        """
        from config.settings import get_settings

        settings = get_settings()
        screenshots_dir = Path(settings.screenshots_dir)
        filename = f"{timestamp_str()}_{slugify(url)[:60]}.png"
        path = screenshots_dir / filename
        try:
            await self._browser.take_screenshot(path)
        except Exception as exc:
            self._log.warning("Screenshot failed for {url}: {exc}", url=url, exc=exc)

    async def crawl(
        self, urls: list[str], output_path: Path
    ) -> CrawlResult:
        """Orchestrate the full crawl pipeline over *urls*.

        For each URL: rate-limit → fetch → parse → validate → clean.  All
        extracted records are accumulated then saved together.

        Args:
            urls: Ordered list of URLs to crawl.
            output_path: Destination file for saved records.

        Returns:
            Populated :class:`CrawlResult`.
        """
        result = self.start()
        all_records: list[dict[str, Any]] = []

        async with self._browser:
            for url in urls:
                await self._rate_limiter.wait()
                await self._crawl_one(url, result, all_records)

        if all_records:
            rows = self.save(all_records, output_path)
            result.records_extracted = rows
            result.output_path = str(output_path)

        return self.finish(result)

    async def _crawl_one(
        self,
        url: str,
        result: CrawlResult,
        all_records: list[dict[str, Any]],
    ) -> None:
        """Fetch a single *url* and accumulate parsed records into *all_records*.

        Errors are logged and appended to ``result.errors``; they do not abort
        the overall crawl.

        Args:
            url: URL to fetch.
            result: Running :class:`CrawlResult` to update.
            all_records: Mutable list to append extracted records to.
        """
        self._log.debug("Fetching {url}", url=url)
        try:
            page = await self.fetch(url)
            result.pages_fetched += 1
            raw = self.parse(page)
            valid = self.validate(raw)
            cleaned = self.clean(valid)
            all_records.extend(cleaned)
            self._log.debug(
                "Fetched {url}: {n} records extracted", url=url, n=len(cleaned)
            )
        except Exception as exc:
            msg = f"Failed to crawl {url}: {exc}"
            self._log.error(msg)
            result.errors.append(msg)
            if self.profile.screenshot_on_failure:
                await self._take_screenshot(url)

    async def run(self, urls: list[str], output_path: Path) -> CrawlResult:
        """Public entry point — calls :meth:`crawl` with top-level error handling.

        Args:
            urls: URLs to crawl.
            output_path: Destination Parquet file.

        Returns:
            Final :class:`CrawlResult`.
        """
        from crawlers.base.models import CrawlStatus

        try:
            return await self.crawl(urls, output_path)
        except Exception as exc:
            self._log.exception("Unhandled error in crawler '{name}': {exc}", name=self.profile.name, exc=exc)
            result = self.start()
            result.status = CrawlStatus.FAILED
            result.errors.append(str(exc))
            result.ended_at = datetime.now(tz=UTC)
            return result
