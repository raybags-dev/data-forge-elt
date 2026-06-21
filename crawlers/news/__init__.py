"""News crawler package for DataForge ELT."""

from crawlers.news.crawler import NewsCrawler
from crawlers.news.models import NewsArticle
from crawlers.news.parser import NewsParser

__all__ = [
    "NewsCrawler",
    "NewsArticle",
    "NewsParser",
]
