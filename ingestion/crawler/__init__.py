"""Crawler ingestion subpackage.

Exports CrawlerIngestor and IngestionResult.
"""

from __future__ import annotations

from ingestion.crawler.ingestor import CrawlerIngestor
from ingestion.crawler.models import IngestionResult

__all__ = [
    "CrawlerIngestor",
    "IngestionResult",
]
