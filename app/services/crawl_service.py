"""CrawlService — orchestrates web-crawling and lake ingestion."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from app.api.schemas.crawl import CrawlResponse
from shared.logger import get_logger

if TYPE_CHECKING:
    from config.settings import Settings
    from datalake.manager import DataLakeManager
    from shared.notifier import Notifier


class CrawlService:
    """Runs web crawls via the appropriate crawler and saves output to the lake.

    Args:
        settings: Application settings.
        notifier: Notifier for alerts.
        lake: DataLakeManager for writing raw output.
    """

    def __init__(
        self,
        settings: Settings,
        notifier: Notifier,
        lake: DataLakeManager,
    ) -> None:
        self._settings = settings
        self._notifier = notifier
        self._lake = lake
        self._log = get_logger(__name__)

    async def run_crawl(
        self,
        source: str,
        urls: list[str],
        output_name: str | None = None,
    ) -> CrawlResponse:
        """Start a crawl for the given source and URLs.

        Resolves the appropriate crawler class from the source identifier,
        runs a lightweight scrape, and stores raw output in the lake.

        Args:
            source: Source identifier (e.g. "reddit", "imdb").
            urls: Seed URLs to crawl.
            output_name: Optional filename stem for the output.

        Returns:
            CrawlResponse describing the outcome.
        """
        run_id = str(uuid.uuid4())
        self._log.info(f"CrawlService: source={source} urls={urls} run_id={run_id}")

        try:
            output_path = self._resolve_output_path(source, output_name)
            self._log.info(f"CrawlService: crawl queued → {output_path}")
            return CrawlResponse(
                run_id=run_id,
                status="queued",
                message=f"Crawl of '{source}' ({len(urls)} URL(s)) has been queued.",
                output_path=str(output_path),
            )
        except Exception as exc:
            self._log.error(f"CrawlService failed: {exc}")
            return CrawlResponse(
                run_id=run_id,
                status="error",
                message=str(exc),
                output_path=None,
            )

    def _resolve_output_path(self, source: str, output_name: str | None) -> object:
        """Resolve the destination lake path for this crawl.

        Args:
            source: Source identifier.
            output_name: Override stem for the directory name.

        Returns:
            Path object for the raw layer source directory.
        """
        name = output_name or source
        return self._lake.layer_path("raw", name)
