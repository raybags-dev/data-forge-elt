"""Ingestion loaders subpackage.

Exports ParquetLoader and DuckDBLoader.
"""

from __future__ import annotations

from ingestion.loaders.duckdb_loader import DuckDBLoader
from ingestion.loaders.parquet_loader import ParquetLoader

__all__ = [
    "ParquetLoader",
    "DuckDBLoader",
]
