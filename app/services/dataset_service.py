"""DatasetService — lists and previews lake datasets."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.api.schemas.datasets import DatasetItem, DatasetListResponse
from shared.logger import get_logger

if TYPE_CHECKING:
    from config.settings import Settings
    from datalake.manager import DataLakeManager


class DatasetService:
    """Provides dataset discovery and preview for the API layer.

    Scans the data lake for Parquet files and reads them on demand.
    Falls back to S3 listing when configured.

    Args:
        lake: DataLakeManager instance for accessing lake files.
        settings: Application settings (for S3 config).
    """

    def __init__(self, lake: DataLakeManager, settings: Settings | None = None) -> None:
        self._lake = lake
        self._settings = settings
        self._log = get_logger(__name__)

    def list_datasets(self) -> DatasetListResponse:
        """Scan all lake layers for Parquet files and return metadata.

        Returns:
            DatasetListResponse with all discovered datasets.
        """
        items: list[DatasetItem] = []

        for layer in self._lake.LAYERS:
            try:
                entries = self._lake.list_entries(layer)
                for entry in entries:
                    items.append(
                        DatasetItem(
                            source=entry.source,
                            layer=entry.layer,
                            name=entry.filename,
                            path=str(entry.path),
                            size_bytes=entry.size_bytes,
                            created_at=entry.created_at.isoformat(),
                        )
                    )
            except Exception as exc:
                self._log.warning(f"DatasetService: could not list layer '{layer}': {exc}")

        # S3 supplement — list any objects in s3://bucket/raw/ not already found locally
        if self._settings:
            try:
                from shared.storage_s3 import is_configured, list_objects
                if is_configured(self._settings):
                    seen_names = {it.name for it in items}
                    for obj in list_objects(self._settings, prefix="raw/"):
                        key = obj["Key"]  # e.g. raw/reddit_posts/data.parquet
                        parts = key.split("/")
                        if len(parts) >= 3 and key.endswith(".parquet"):
                            fname = parts[-1]
                            if fname not in seen_names:
                                items.append(DatasetItem(
                                    source="s3",
                                    layer="raw",
                                    name=fname,
                                    path=f"s3://{self._settings.aws_s3_bucket}/{key}",
                                    size_bytes=obj.get("Size", 0),
                                    created_at=obj["LastModified"].isoformat() if "LastModified" in obj else "",
                                ))
                                seen_names.add(fname)
            except Exception as exc:
                self._log.debug(f"DatasetService: S3 listing skipped: {exc}")

        self._log.info(f"DatasetService: found {len(items)} dataset(s)")
        return DatasetListResponse(datasets=items, total=len(items))

    def get_preview(self, source: str, name: str) -> list[dict]:
        """Read the first 100 rows of a dataset from the lake.

        Searches across all layers for a file matching source/name.

        Args:
            source: Source identifier.
            name: Filename (with or without .parquet extension).

        Returns:
            List of row dicts (up to 100 rows).
        """
        import pandas as pd

        target_name = name if name.endswith(".parquet") else f"{name}.parquet"

        for layer in self._lake.LAYERS:
            try:
                entries = self._lake.list_entries(layer, source)
                for entry in entries:
                    if entry.filename == target_name or entry.filename == name:
                        df = pd.read_parquet(entry.path, engine="pyarrow")
                        return df.head(100).to_dict(orient="records")
            except Exception as exc:
                self._log.warning(
                    f"DatasetService: preview failed for {source}/{name} in {layer}: {exc}"
                )

        return []
