"""DatasetService — lists and previews lake datasets."""

from __future__ import annotations

from typing import TYPE_CHECKING

from shared.logger import get_logger

from app.api.schemas.datasets import DatasetItem, DatasetListResponse

if TYPE_CHECKING:
    from datalake.manager import DataLakeManager


class DatasetService:
    """Provides dataset discovery and preview for the API layer.

    Scans the data lake for Parquet files and reads them on demand.

    Args:
        lake: DataLakeManager instance for accessing lake files.
    """

    def __init__(self, lake: "DataLakeManager") -> None:
        self._lake = lake
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
