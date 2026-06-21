"""News article crawler for DataForge ELT."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from crawlers.base.crawler import BaseCrawler
from crawlers.base.models import CrawledPage, CrawlerProfile
from crawlers.news.models import NewsArticle
from crawlers.news.parser import NewsParser
from shared.logger import get_logger

if TYPE_CHECKING:
    from config.settings import Settings
    from crawlers.base.browser import BrowserManager
    from crawlers.base.rate_limit import RateLimiter
    from shared.notifier import Notifier

_log = get_logger(__name__)


class NewsCrawler(BaseCrawler):
    """Crawls generic news websites and extracts article data.

    Args:
        profile: Crawler configuration profile.
        browser_manager: Playwright browser lifecycle manager.
        rate_limiter: Token-bucket rate limiter.
        notifier: Notification channel.
        parser: Optional :class:`NewsParser` (injected for testing).
    """

    DEFAULT_PROFILE: CrawlerProfile = CrawlerProfile(
        name="news",
        base_url="https://news.ycombinator.com",
        timeout=30,
        headless=True,
        max_retries=3,
        rate_limit_rps=1.0,
        robots_txt_compliance=True,
        screenshot_on_failure=True,
        headers={"Accept-Language": "en-US,en;q=0.9"},
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
    )

    def __init__(
        self,
        profile: CrawlerProfile,
        browser_manager: BrowserManager,
        rate_limiter: RateLimiter,
        notifier: Notifier,
        parser: NewsParser | None = None,
    ) -> None:
        super().__init__(
            profile=profile,
            browser_manager=browser_manager,
            rate_limiter=rate_limiter,
            notifier=notifier,
            logger=_log,
        )
        self._parser = parser or NewsParser()

    @classmethod
    def build(
        cls,
        settings: Settings,
        notifier: Notifier,
        profile: CrawlerProfile | None = None,
    ) -> NewsCrawler:
        """Factory — builds a fully-wired :class:`NewsCrawler`.

        Args:
            settings: Application settings.
            notifier: Notification channel.
            profile: Override profile; defaults to :attr:`DEFAULT_PROFILE`.
        """
        from crawlers.base.browser import BrowserManager
        from crawlers.base.rate_limit import build_rate_limiter

        active_profile = profile or cls.DEFAULT_PROFILE
        browser = BrowserManager(active_profile, settings)
        limiter = build_rate_limiter(settings)
        return cls(
            profile=active_profile,
            browser_manager=browser,
            rate_limiter=limiter,
            notifier=notifier,
        )

    async def fetch(self, url: str) -> CrawledPage:
        """Navigate to *url* via the managed browser.

        Args:
            url: News page URL.
        """
        return await self._browser.navigate(url)

    def parse(self, page: CrawledPage) -> list[dict[str, Any]]:
        """Delegate HTML parsing to :class:`NewsParser`.

        Args:
            page: Fetched page snapshot.
        """
        articles = self._parser.parse_page(page)
        return [a.model_dump() for a in articles]

    def validate(self, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Validate records by round-tripping through :class:`NewsArticle`.

        Args:
            records: Raw dicts from :meth:`parse`.
        """
        valid: list[dict[str, Any]] = []
        for record in records:
            try:
                NewsArticle.model_validate(record)
                valid.append(record)
            except Exception as exc:
                _log.debug("Dropping invalid news record: {exc}", exc=exc)
        return valid
