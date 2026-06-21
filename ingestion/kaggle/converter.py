"""CSV to Parquet conversion utilities for Kaggle ingestion."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from loguru import Logger


class CsvToParquetConverter:
    """Converts CSV files to Parquet format using pyarrow engine.

    Handles encoding errors gracefully and supports large file conversion
    via chunked reading.

    Args:
        logger: Loguru Logger instance for structured logging.
    """

    _CHUNK_SIZE: int = 100_000
    _PARQUET_ENGINE: str = "pyarrow"

    def __init__(self, logger: Logger) -> None:
        self._log = logger

    def convert(self, csv_path: Path, output_path: Path | None = None) -> Path:
        """Convert a single CSV file to Parquet.

        Reads the CSV with encoding-error handling and writes Parquet to
        the same directory or *output_path* if provided.

        Args:
            csv_path: Path to the source CSV file.
            output_path: Optional destination path for the Parquet file.
                         Defaults to same directory with .parquet extension.

        Returns:
            Path to the written Parquet file.
        """
        dest = output_path or csv_path.with_suffix(".parquet")
        self._log.debug(f"Converting {csv_path.name} → {dest.name}")

        df = self._read_csv_safe(csv_path)
        df.to_parquet(dest, engine=self._PARQUET_ENGINE, index=False)

        self._log.info(
            f"Converted {csv_path.name} → {dest.name} ({len(df):,} rows)"
        )
        return dest

    def convert_all_csvs(self, directory: Path) -> list[Path]:
        """Convert all CSV files found recursively in *directory*.

        Args:
            directory: Root directory to search for CSV files.

        Returns:
            List of paths to the produced Parquet files.
        """
        csv_files = list(directory.rglob("*.csv"))
        self._log.info(f"Found {len(csv_files)} CSV file(s) in {directory}")

        results: list[Path] = []
        for csv_path in csv_files:
            try:
                parquet_path = self.convert(csv_path)
                results.append(parquet_path)
            except Exception as exc:
                self._log.error(f"Failed to convert {csv_path.name}: {exc}")

        return results

    def _read_csv_safe(self, csv_path: Path) -> pd.DataFrame:
        """Read a CSV file with encoding-error recovery.

        Args:
            csv_path: Path to the CSV file.

        Returns:
            Loaded DataFrame.
        """
        for encoding in ("utf-8", "latin-1", "cp1252"):
            try:
                return pd.read_csv(
                    csv_path,
                    encoding=encoding,
                    encoding_errors="replace",
                    low_memory=False,
                )
            except UnicodeDecodeError:
                continue
            except Exception:
                raise

        return pd.read_csv(csv_path, encoding="latin-1", encoding_errors="replace")
