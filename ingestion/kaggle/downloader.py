"""Kaggle dataset downloader with auth, search, and conversion."""

from __future__ import annotations

import os
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

from shared.exceptions import ConfigError, DownloadError
from shared.notifier import NotificationLevel, NotificationPayload
from shared.retry import network_retry

if TYPE_CHECKING:
    from config.settings import Settings
    from loguru import Logger

    from shared.notifier import Notifier

from ingestion.kaggle.converter import CsvToParquetConverter
from ingestion.kaggle.models import DownloadResult, KaggleDataset


class KaggleDownloader:
    """Downloads Kaggle datasets, extracts ZIPs, and converts CSVs to Parquet.

    Args:
        settings: Application settings containing Kaggle credentials.
        notifier: Notifier instance for completion/failure alerts.
        logger: Loguru Logger for structured logging.
    """

    def __init__(
        self,
        settings: "Settings",
        notifier: "Notifier",
        logger: "Logger",
    ) -> None:
        self._settings = settings
        self._notifier = notifier
        self._log = logger
        self._converter = CsvToParquetConverter(logger=logger)
        self._api: Any = None

    def _setup_kaggle_auth(self) -> Any:
        """Configure Kaggle environment variables and return the API client.

        Raises:
            ConfigError: If Kaggle credentials are missing from settings.

        Returns:
            Authenticated kaggle.api instance.
        """
        username = self._settings.kaggle_username
        key = self._settings.kaggle_key

        if not username or not key:
            raise ConfigError(
                "Kaggle credentials not configured. "
                "Set KAGGLE_USERNAME and KAGGLE_KEY in your environment or .env file."
            )

        os.environ["KAGGLE_USERNAME"] = username
        os.environ["KAGGLE_KEY"] = key

        from kaggle.api.kaggle_api_extended import KaggleApiExtended

        api = KaggleApiExtended()
        api.authenticate()
        return api

    def _get_api(self) -> Any:
        """Return cached Kaggle API instance, authenticating on first call."""
        if self._api is None:
            self._api = self._setup_kaggle_auth()
        return self._api

    @network_retry
    def search(self, query: str, max_results: int = 10) -> list[KaggleDataset]:
        """Search Kaggle for public datasets matching *query*.

        Args:
            query: Search term.
            max_results: Maximum number of results to return.

        Returns:
            List of KaggleDataset objects matching the query.
        """
        api = self._get_api()
        self._log.info(f"Searching Kaggle for '{query}' (max={max_results})")

        raw = api.dataset_list(search=query, max_size=None, page=1)
        results: list[KaggleDataset] = []

        for item in raw[:max_results]:
            dataset = self._build_dataset_from_api(item)
            results.append(dataset)

        self._log.info(f"Found {len(results)} dataset(s)")
        return results

    def download(self, dataset: KaggleDataset, force: bool = False) -> DownloadResult:
        """Download a Kaggle dataset, extract it, and convert CSVs to Parquet.

        Args:
            dataset: The KaggleDataset to download.
            force: If True, re-download even if files already exist.

        Returns:
            DownloadResult with paths, row counts, and status.
        """
        start = time.monotonic()
        timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%S")
        dest_dir = (
            Path(self._settings.data_lake)
            / "raw"
            / dataset.name
            / timestamp
        )
        dest_dir.mkdir(parents=True, exist_ok=True)

        self._log.info(f"Downloading {dataset.full_name} → {dest_dir}")

        try:
            result = self._do_download(dataset, dest_dir, force, start)
        except Exception as exc:
            duration = time.monotonic() - start
            self._log.error(f"Download failed for {dataset.full_name}: {exc}")
            self._send_failure_notification(dataset, str(exc))
            return DownloadResult(
                dataset=dataset,
                download_path=dest_dir,
                parquet_files=[],
                rows_total=0,
                success=False,
                error=str(exc),
                duration_seconds=duration,
            )

        return result

    def _do_download(
        self,
        dataset: KaggleDataset,
        dest_dir: Path,
        force: bool,
        start: float,
    ) -> DownloadResult:
        """Execute the actual download, extraction, and conversion pipeline.

        Args:
            dataset: Target Kaggle dataset.
            dest_dir: Destination directory for downloaded files.
            force: Whether to overwrite existing files.
            start: Monotonic start time for duration tracking.

        Returns:
            Successful DownloadResult.
        """
        api = self._get_api()
        api.dataset_download_files(
            dataset.full_name,
            path=str(dest_dir),
            unzip=False,
            force=force,
            quiet=True,
        )

        self._extract_zips(dest_dir)
        parquet_files = self._converter.convert_all_csvs(dest_dir)
        rows_total = self._count_rows(parquet_files)
        duration = time.monotonic() - start

        self._log.info(
            f"Download complete: {dataset.full_name} | "
            f"{len(parquet_files)} parquet file(s) | {rows_total:,} rows | "
            f"{duration:.1f}s"
        )
        self._send_success_notification(dataset, parquet_files, rows_total, duration)

        return DownloadResult(
            dataset=dataset,
            download_path=dest_dir,
            parquet_files=parquet_files,
            rows_total=rows_total,
            success=True,
            duration_seconds=duration,
        )

    def _extract_zips(self, directory: Path) -> None:
        """Extract all ZIP archives found in *directory*.

        Args:
            directory: Directory to scan for ZIP files.
        """
        for zip_path in directory.glob("*.zip"):
            self._log.debug(f"Extracting {zip_path.name}")
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(directory)
            zip_path.unlink()

    def _count_rows(self, parquet_files: list[Path]) -> int:
        """Count total rows across all Parquet files.

        Args:
            parquet_files: List of Parquet file paths.

        Returns:
            Total row count.
        """
        import pandas as pd

        total = 0
        for path in parquet_files:
            try:
                df = pd.read_parquet(path, engine="pyarrow")
                total += len(df)
            except Exception as exc:
                self._log.warning(f"Could not count rows in {path.name}: {exc}")
        return total

    def _build_dataset_from_api(self, item: Any) -> KaggleDataset:
        """Convert a raw Kaggle API result into a KaggleDataset.

        Args:
            item: Raw dataset object returned by kaggle API.

        Returns:
            KaggleDataset instance.
        """
        ref = str(getattr(item, "ref", "") or "")
        parts = ref.split("/")
        owner = parts[0] if len(parts) >= 1 else ""
        name = parts[1] if len(parts) >= 2 else ref

        return KaggleDataset(
            owner=owner,
            name=name,
            full_name=ref,
            description=str(getattr(item, "subtitle", "") or ""),
            size_bytes=getattr(item, "totalBytes", None),
            file_count=getattr(item, "fileCount", None),
            last_updated=getattr(item, "lastUpdated", None),
        )

    def _send_success_notification(
        self,
        dataset: KaggleDataset,
        parquet_files: list[Path],
        rows_total: int,
        duration: float,
    ) -> None:
        """Send a success notification after a completed download.

        Args:
            dataset: The downloaded dataset.
            parquet_files: Resulting parquet file paths.
            rows_total: Total rows across all files.
            duration: Elapsed seconds.
        """
        self._notifier.send(
            NotificationPayload(
                title="Kaggle Download Complete",
                message=f"Dataset '{dataset.full_name}' downloaded successfully.",
                level=NotificationLevel.INFO,
                details={
                    "parquet_files": len(parquet_files),
                    "rows_total": rows_total,
                    "duration_seconds": round(duration, 2),
                },
            )
        )

    def _send_failure_notification(
        self, dataset: KaggleDataset, error: str
    ) -> None:
        """Send a failure notification after a failed download.

        Args:
            dataset: The dataset that failed to download.
            error: Error message string.
        """
        self._notifier.send(
            NotificationPayload(
                title="Kaggle Download Failed",
                message=f"Dataset '{dataset.full_name}' download failed: {error}",
                level=NotificationLevel.ERROR,
            )
        )
