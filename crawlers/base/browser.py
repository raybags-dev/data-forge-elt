"""Playwright-based browser manager for the DataForge crawler engine.

Wraps the Playwright async API and exposes a clean interface used by
:class:`crawlers.base.crawler.BaseCrawler`.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from shared.logger import get_logger

if TYPE_CHECKING:
    from playwright.async_api import Browser, BrowserContext, Page, Playwright

    from config.settings import Settings
    from crawlers.base.models import CrawledPage, CrawlerProfile

_log = get_logger(__name__)


class BrowserManager:
    """Manages the lifecycle of a Playwright browser instance.

    One :class:`BrowserManager` is created per crawler run.  Use it as an
    async context manager or call :meth:`start` / :meth:`stop` explicitly.

    Attributes:
        profile: The :class:`CrawlerProfile` supplying browser configuration.
    """

    def __init__(self, profile: "CrawlerProfile", settings: "Settings") -> None:
        """Initialise the manager without launching the browser.

        Args:
            profile: Crawler profile (user-agent, headers, cookies, proxy, …).
            settings: Application settings (timeout, headless flag, …).
        """
        self.profile: "CrawlerProfile" = profile
        self._settings: "Settings" = settings
        self._playwright: "Playwright | None" = None
        self._browser: "Browser | None" = None
        self._context: "BrowserContext | None" = None
        self._page: "Page | None" = None

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def start(self) -> None:
        """Launch Playwright, open a Chromium browser, and create a page.

        Raises:
            RuntimeError: If the manager is already running.
        """
        if self._playwright is not None:
            raise RuntimeError("BrowserManager is already running.")

        from playwright.async_api import async_playwright

        _log.debug("Starting Playwright browser for profile '{name}'", name=self.profile.name)
        self._playwright = await async_playwright().start()
        launch_opts: dict[str, Any] = {"headless": self._settings.headless}
        if self.profile.proxy:
            launch_opts["proxy"] = {"server": self.profile.proxy}

        self._browser = await self._playwright.chromium.launch(**launch_opts)
        context_opts: dict[str, Any] = {
            "user_agent": self.profile.user_agent,
            "extra_http_headers": self.profile.headers,
        }
        self._context = await self._browser.new_context(**context_opts)

        if self.profile.cookies:
            cookies = [
                {"name": k, "value": v, "url": self.profile.base_url}
                for k, v in self.profile.cookies.items()
            ]
            await self._context.add_cookies(cookies)

        self._page = await self._context.new_page()
        _log.info("Browser ready for profile '{name}'", name=self.profile.name)

    async def stop(self) -> None:
        """Close the page, context, browser, and Playwright in order.

        Always completes — individual close errors are logged but not raised.
        """
        _log.debug("Stopping browser for profile '{name}'", name=self.profile.name)
        try:
            if self._page:
                await self._page.close()
        except Exception as exc:
            _log.warning("Error closing page: {exc}", exc=exc)
        finally:
            self._page = None

        try:
            if self._context:
                await self._context.close()
        except Exception as exc:
            _log.warning("Error closing browser context: {exc}", exc=exc)
        finally:
            self._context = None

        try:
            if self._browser:
                await self._browser.close()
        except Exception as exc:
            _log.warning("Error closing browser: {exc}", exc=exc)
        finally:
            self._browser = None

        try:
            if self._playwright:
                await self._playwright.stop()
        except Exception as exc:
            _log.warning("Error stopping Playwright: {exc}", exc=exc)
        finally:
            self._playwright = None

        _log.info("Browser stopped for profile '{name}'", name=self.profile.name)

    # ── Context manager ───────────────────────────────────────────────────────

    async def __aenter__(self) -> "BrowserManager":
        """Start the browser and return ``self``."""
        await self.start()
        return self

    async def __aexit__(self, *_: object) -> None:
        """Stop the browser regardless of whether an exception occurred."""
        await self.stop()

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def is_running(self) -> bool:
        """``True`` if the browser has been started and not yet stopped."""
        return self._page is not None

    # ── Page operations ───────────────────────────────────────────────────────

    async def get_page(self) -> "Page":
        """Return the active Playwright :class:`Page`.

        Raises:
            RuntimeError: If the browser has not been started.
        """
        if self._page is None:
            raise RuntimeError("BrowserManager is not running. Call start() first.")
        return self._page

    async def navigate(self, url: str) -> "CrawledPage":
        """Navigate to *url* and return a :class:`CrawledPage` snapshot.

        Args:
            url: Fully-qualified URL to load.

        Returns:
            A :class:`CrawledPage` populated from the page response.

        Raises:
            RuntimeError: If the browser has not been started.
        """
        from datetime import timezone, datetime

        from crawlers.base.models import CrawledPage

        page = await self.get_page()
        timeout_ms = self.profile.timeout * 1000
        t_start = time.monotonic()

        response = await page.goto(url, timeout=timeout_ms, wait_until="load")
        response_time_ms = int((time.monotonic() - t_start) * 1000)

        html = await page.content()
        text = await page.evaluate("document.body?.innerText ?? ''")
        title = await page.title() or None
        status_code = response.status if response else 0
        headers: dict[str, Any] = dict(response.headers) if response else {}

        return CrawledPage(
            url=page.url,
            status_code=status_code,
            html=html,
            text=text,
            title=title,
            headers=headers,
            loaded_at=datetime.now(tz=timezone.utc),
            response_time_ms=response_time_ms,
        )

    async def take_screenshot(self, path: Path) -> None:
        """Save a full-page screenshot to *path*.

        Args:
            path: Destination file path (PNG format).

        Raises:
            RuntimeError: If the browser has not been started.
        """
        page = await self.get_page()
        path.parent.mkdir(parents=True, exist_ok=True)
        await page.screenshot(path=str(path), full_page=True)
        _log.debug("Screenshot saved to {path}", path=path)
