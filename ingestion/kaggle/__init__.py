"""Kaggle ingestion subpackage.

Exports KaggleDownloader, CsvToParquetConverter, and data models.
"""

from __future__ import annotations

from ingestion.kaggle.converter import CsvToParquetConverter
from ingestion.kaggle.downloader import KaggleDownloader
from ingestion.kaggle.models import DownloadResult, KaggleDataset

__all__ = [
    "KaggleDataset",
    "DownloadResult",
    "KaggleDownloader",
    "CsvToParquetConverter",
]
