"""Public API for the DataForge crawler base package.

Exports:
    - Models: CrawlerProfile, CrawledPage, CrawlResult, CrawlStatus
    - BaseCrawler: abstract base class for all crawlers
    - BrowserManager: Playwright browser lifecycle manager
    - RateLimiter, build_rate_limiter: token-bucket rate limiting
    - RobotsChecker: robots.txt compliance
    - PaginationStrategy, NoPagination, PageNumberStrategy, CursorStrategy
"""

from crawlers.base.browser import BrowserManager
from crawlers.base.crawler import BaseCrawler
from crawlers.base.models import CrawledPage, CrawlerProfile, CrawlResult, CrawlStatus
from crawlers.base.pagination import (
    CursorStrategy,
    NoPagination,
    PageNumberStrategy,
    PaginationStrategy,
)
from crawlers.base.rate_limit import RateLimiter, build_rate_limiter
from crawlers.base.robots import RobotsChecker

__all__ = [
    "BaseCrawler",
    "BrowserManager",
    "CrawledPage",
    "CrawlResult",
    "CrawlStatus",
    "CrawlerProfile",
    "CursorStrategy",
    "NoPagination",
    "PageNumberStrategy",
    "PaginationStrategy",
    "RateLimiter",
    "RobotsChecker",
    "build_rate_limiter",
]
