"""Data lake manager — reads and writes across lake layers."""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd

from datalake.models import DataLakeEntry
from datalake.versioning import DataVersionManager
from shared.utils import timestamp_str

if TYPE_CHECKING:
    from loguru import Logger


class DataLakeManager:
    """Manages the multi-layer data lake (raw → bronze → silver → gold).

    All writes are partitioned by date (YYYY/MM/DD) and versioned with
    timestamps to support idempotent re-runs and time-travel queries.

    Args:
        base_path: Root filesystem path for the data lake.
        logger: Loguru Logger for structured logging.
    """

    LAYERS: list[str] = ["raw", "bronze", "silver", "gold"]

    def __init__(self, base_path: Path, logger: Logger) -> None:
        self._base = base_path
        self._log = logger
        self._versioner = DataVersionManager()

    def setup(self) -> None:
        """Create all layer directories under the base path.

        Idempotent — safe to call multiple times.
        """
        for layer in self.LAYERS:
            layer_dir = self._base / layer
            layer_dir.mkdir(parents=True, exist_ok=True)
            self._log.debug(f"Ensured layer directory: {layer_dir}")
        self._log.info(f"Data lake ready at {self._base}")

    def layer_path(self, layer: str, source: str) -> Path:
        """Return the base directory for *layer*/*source*.

        Args:
            layer: Lake layer name (raw, bronze, silver, gold).
            source: Source identifier.

        Returns:
            Path to the layer/source directory (not guaranteed to exist).
        """
        self._validate_layer(layer)
        return self._base / layer / source

    def write_parquet(
        self,
        layer: str,
        source: str,
        df: pd.DataFrame,
        filename: str | None = None,
    ) -> Path:
        """Write a DataFrame as Parquet to the appropriate dated partition.

        Args:
            layer: Target lake layer.
            source: Source identifier.
            df: DataFrame to write.
            filename: Optional filename; auto-generated timestamp if omitted.

        Returns:
            Absolute path of the written Parquet file.
        """
        self._validate_layer(layer)
        src_path = self.layer_path(layer, source)
        dated_dir = self._versioner.current_version_path(src_path)

        fname = filename or f"{timestamp_str()}.parquet"
        if not fname.endswith(".parquet"):
            fname = f"{fname}.parquet"

        dest = dated_dir / fname
        df.to_parquet(dest, engine="pyarrow", index=False)

        self._log.info(
            f"Wrote {len(df):,} rows → {dest} (layer={layer}, source={source})"
        )
        return dest

    def read_parquet(
        self,
        layer: str,
        source: str,
        dt: date | None = None,
    ) -> pd.DataFrame:
        """Read all Parquet files from *layer*/*source*, optionally filtered by date.

        Args:
            layer: Lake layer to read from.
            source: Source identifier.
            dt: If provided, only reads files from that date's partition.

        Returns:
            Concatenated DataFrame (empty if no files found).
        """
        self._validate_layer(layer)
        src_path = self.layer_path(layer, source)

        scan_root = self._versioner.get_version_path(src_path, dt) if dt is not None else src_path

        files = sorted(scan_root.rglob("*.parquet")) if scan_root.exists() else []
        self._log.info(
            f"Reading {len(files)} parquet file(s) from {scan_root}"
        )

        if not files:
            return pd.DataFrame()

        frames = [pd.read_parquet(f, engine="pyarrow") for f in files]
        return pd.concat(frames, ignore_index=True)

    def list_entries(
        self, layer: str, source: str | None = None
    ) -> list[DataLakeEntry]:
        """Return metadata entries for all Parquet files in *layer*.

        Args:
            layer: Lake layer to inspect.
            source: Optional source filter; if None, all sources are returned.

        Returns:
            List of DataLakeEntry objects.
        """
        self._validate_layer(layer)
        layer_root = self._base / layer

        if not layer_root.exists():
            return []

        entries: list[DataLakeEntry] = []
        scan_root = layer_root / source if source else layer_root

        for parquet_file in sorted(scan_root.rglob("*.parquet")):
            entry = self._build_entry(layer, parquet_file, layer_root)
            entries.append(entry)

        return entries

    def promote(
        self,
        source_layer: str,
        dest_layer: str,
        source: str,
        df: pd.DataFrame,
    ) -> Path:
        """Promote data from *source_layer* to *dest_layer*.

        Args:
            source_layer: Origin layer name.
            dest_layer: Destination layer name.
            source: Source identifier.
            df: DataFrame to write to the destination layer.

        Returns:
            Path of the written Parquet file in the destination layer.
        """
        self._validate_layer(source_layer)
        self._validate_layer(dest_layer)

        self._log.info(
            f"Promoting '{source}': {source_layer} → {dest_layer} ({len(df):,} rows)"
        )
        return self.write_parquet(dest_layer, source, df)

    def _validate_layer(self, layer: str) -> None:
        """Raise ValueError if *layer* is not a recognised lake layer.

        Args:
            layer: Layer name to validate.
        """
        if layer not in self.LAYERS:
            raise ValueError(
                f"Unknown layer '{layer}'. Must be one of {self.LAYERS}."
            )

    def _build_entry(
        self, layer: str, file_path: Path, layer_root: Path
    ) -> DataLakeEntry:
        """Build a DataLakeEntry for a single Parquet file.

        Args:
            layer: Lake layer name.
            file_path: Absolute path to the Parquet file.
            layer_root: Root directory for the layer (used to extract source).

        Returns:
            DataLakeEntry populated from file metadata.
        """
        relative = file_path.relative_to(layer_root)
        source = relative.parts[0] if len(relative.parts) > 1 else ""
        stat = file_path.stat()
        created_at = datetime.fromtimestamp(stat.st_ctime, tz=UTC)

        return DataLakeEntry(
            layer=layer,
            source=source,
            path=file_path,
            filename=file_path.name,
            created_at=created_at,
            size_bytes=stat.st_size,
        )
