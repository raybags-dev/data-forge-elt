"""Moves crawled data into the data lake raw layer."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd

from ingestion.crawler.models import IngestionResult

if TYPE_CHECKING:
    from loguru import Logger

    from datalake.manager import DataLakeManager


class CrawlerIngestor:
    """Ingests crawled data files into the data lake raw layer.

    Moves or copies Parquet/JSON files produced by web crawlers into
    their designated raw layer directory in the data lake.

    Args:
        lake_manager: DataLakeManager for writing data to the lake.
        logger: Loguru Logger instance.
    """

    def __init__(self, lake_manager: "DataLakeManager", logger: "Logger") -> None:
        self._lake = lake_manager
        self._log = logger

    def ingest_dataframe(
        self,
        source: str,
        df: pd.DataFrame,
        filename: str | None = None,
    ) -> IngestionResult:
        """Ingest a pandas DataFrame into the raw data lake layer.

        Args:
            source: Source name used for the data lake sub-directory.
            df: DataFrame to ingest.
            filename: Optional filename; auto-generated if omitted.

        Returns:
            IngestionResult describing the outcome.
        """
        self._log.info(f"Ingesting DataFrame for source='{source}' ({len(df):,} rows)")
        try:
            output_path = self._lake.write_parquet("raw", source, df, filename)
            return IngestionResult(
                source=source,
                layer="raw",
                files_ingested=1,
                rows_total=len(df),
                output_path=output_path,
                success=True,
            )
        except Exception as exc:
            self._log.error(f"Ingestion failed for {source}: {exc}")
            return IngestionResult(
                source=source,
                layer="raw",
                files_ingested=0,
                rows_total=0,
                output_path=Path("."),
                success=False,
                error=str(exc),
            )

    def ingest_file(self, source: str, file_path: Path) -> IngestionResult:
        """Ingest a single Parquet file into the raw data lake layer.

        Args:
            source: Source name for the lake sub-directory.
            file_path: Path to the Parquet file to ingest.

        Returns:
            IngestionResult describing the outcome.
        """
        self._log.info(f"Ingesting file {file_path.name} for source='{source}'")
        try:
            df = pd.read_parquet(file_path)
            output_path = self._lake.write_parquet(
                "raw", source, df, file_path.name
            )
            return IngestionResult(
                source=source,
                layer="raw",
                files_ingested=1,
                rows_total=len(df),
                output_path=output_path,
                success=True,
            )
        except Exception as exc:
            self._log.error(f"File ingestion failed for {file_path.name}: {exc}")
            return IngestionResult(
                source=source,
                layer="raw",
                files_ingested=0,
                rows_total=0,
                output_path=Path("."),
                success=False,
                error=str(exc),
            )

    def ingest_directory(self, source: str, directory: Path) -> IngestionResult:
        """Ingest all Parquet files from *directory* into the raw layer.

        Args:
            source: Source name for the lake sub-directory.
            directory: Directory containing Parquet files.

        Returns:
            IngestionResult with aggregated file and row counts.
        """
        parquet_files = list(directory.rglob("*.parquet"))
        self._log.info(
            f"Ingesting {len(parquet_files)} file(s) from {directory} for source='{source}'"
        )

        total_rows = 0
        files_ok = 0
        last_path: Path = directory

        for file_path in parquet_files:
            result = self.ingest_file(source, file_path)
            if result.success:
                total_rows += result.rows_total
                files_ok += 1
                last_path = result.output_path

        return IngestionResult(
            source=source,
            layer="raw",
            files_ingested=files_ok,
            rows_total=total_rows,
            output_path=last_path,
            success=files_ok > 0 or len(parquet_files) == 0,
        )
