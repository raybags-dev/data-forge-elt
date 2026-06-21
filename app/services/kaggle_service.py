"""KaggleService — wraps KaggleDownloader for the API layer."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.api.schemas.kaggle import KaggleDownloadResponse
from shared.logger import get_logger

if TYPE_CHECKING:
    from config.settings import Settings
    from shared.notifier import Notifier


class KaggleService:
    """Downloads Kaggle datasets and returns structured responses.

    Args:
        settings: Application settings with Kaggle credentials.
        notifier: Notifier for completion/error alerts.
    """

    def __init__(self, settings: Settings, notifier: Notifier) -> None:
        self._settings = settings
        self._notifier = notifier
        self._log = get_logger(__name__)

    async def download(
        self, dataset: str, force: bool = False
    ) -> KaggleDownloadResponse:
        """Download a Kaggle dataset by slug.

        Args:
            dataset: Dataset slug in "owner/name" format.
            force: Re-download even if cached.

        Returns:
            KaggleDownloadResponse with result metadata.
        """
        self._log.info(f"KaggleService: downloading dataset={dataset} force={force}")
        try:
            return await self._do_download(dataset, force)
        except Exception as exc:
            self._log.error(f"KaggleService: download failed for {dataset}: {exc}")
            return KaggleDownloadResponse(
                dataset_name=dataset,
                parquet_files=[],
                rows_total=0,
                duration_seconds=0.0,
                success=False,
            )

    async def _do_download(self, dataset: str, force: bool) -> KaggleDownloadResponse:
        """Execute the download using KaggleDownloader.

        Args:
            dataset: Dataset slug.
            force: Force re-download flag.

        Returns:
            KaggleDownloadResponse populated from the DownloadResult.
        """
        from ingestion.kaggle.downloader import KaggleDownloader
        from ingestion.kaggle.models import KaggleDataset

        parts = dataset.split("/", 1)
        owner = parts[0] if len(parts) == 2 else ""
        name = parts[1] if len(parts) == 2 else dataset

        kaggle_dataset = KaggleDataset(owner=owner, name=name)

        downloader = KaggleDownloader(
            settings=self._settings,
            notifier=self._notifier,
            logger=self._log,
        )
        result = downloader.download(kaggle_dataset, force=force)

        return KaggleDownloadResponse(
            dataset_name=dataset,
            parquet_files=[str(p) for p in result.parquet_files],
            rows_total=result.rows_total,
            duration_seconds=result.duration_seconds,
            success=result.success,
        )
