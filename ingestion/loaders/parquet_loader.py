"""Parquet file loader — reads Parquet into pandas DataFrames."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from loguru import Logger


class ParquetLoader:
    """Reads Parquet files from disk into pandas DataFrames.

    Args:
        logger: Loguru Logger for structured logging.
    """

    def __init__(self, logger: Logger) -> None:
        self._log = logger

    def load(self, path: Path) -> pd.DataFrame:
        """Load a single Parquet file into a DataFrame.

        Args:
            path: Path to the Parquet file.

        Returns:
            Loaded DataFrame.

        Raises:
            FileNotFoundError: If *path* does not exist.
        """
        if not path.exists():
            raise FileNotFoundError(f"Parquet file not found: {path}")

        self._log.debug(f"Loading parquet: {path}")
        df = pd.read_parquet(path, engine="pyarrow")
        self._log.info(f"Loaded {len(df):,} rows from {path.name}")
        return df

    def load_directory(
        self, directory: Path, pattern: str = "*.parquet"
    ) -> pd.DataFrame:
        """Load all Parquet files matching *pattern* in *directory*.

        Files are concatenated row-wise into a single DataFrame.

        Args:
            directory: Directory to scan for Parquet files.
            pattern: Glob pattern for file matching.

        Returns:
            Concatenated DataFrame (empty DataFrame if no files found).
        """
        files = sorted(directory.rglob(pattern))
        self._log.info(f"Found {len(files)} parquet file(s) in {directory}")

        if not files:
            return pd.DataFrame()

        frames = [self.load(f) for f in files]
        result = pd.concat(frames, ignore_index=True)
        self._log.info(f"Concatenated {len(result):,} total rows from {directory}")
        return result
