"""DataForge ELT crawler engine.

Exports all crawlers and base infrastructure for easy importing.

Base:
    BaseCrawler, CrawlerProfile, CrawledPage, CrawlResult, CrawlStatus,
    BrowserManager, RateLimiter, RobotsChecker,
    PaginationStrategy, NoPagination, PageNumberStrategy, CursorStrategy

Concrete crawlers:
    RedditCrawler, SteamCrawler, ImdbCrawler, NewsCrawler
"""

from crawlers.base import (
    BaseCrawler,
    BrowserManager,
    CrawledPage,
    CrawlerProfile,
    CrawlResult,
    CrawlStatus,
    CursorStrategy,
    NoPagination,
    PageNumberStrategy,
    PaginationStrategy,
    RateLimiter,
    RobotsChecker,
    build_rate_limiter,
)
from crawlers.imdb import ImdbCrawler
from crawlers.news import NewsCrawler
from crawlers.reddit import RedditCrawler
from crawlers.steam import SteamCrawler

__all__ = [
    # Base infrastructure
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
    # Concrete crawlers
    "ImdbCrawler",
    "NewsCrawler",
    "RedditCrawler",
    "SteamCrawler",
]
