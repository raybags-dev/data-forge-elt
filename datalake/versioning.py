"""Timestamp-based data versioning for the data lake."""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path


class DataVersionManager:
    """Manages dated subdirectories (YYYY/MM/DD) under each data lake source.

    Each write operation is partitioned by date to support time-travel
    and incremental processing patterns.
    """

    def current_version_path(self, layer_path: Path) -> Path:
        """Return the dated subdirectory for today's data in UTC.

        Creates ``layer_path/YYYY/MM/DD`` if it does not exist.

        Args:
            layer_path: Root path for a specific layer/source combination.

        Returns:
            Path to today's dated subdirectory.
        """
        today = date.today()
        dated_dir = layer_path / today.strftime("%Y") / today.strftime("%m") / today.strftime("%d")
        dated_dir.mkdir(parents=True, exist_ok=True)
        return dated_dir

    def get_version_path(self, layer_path: Path, dt: date) -> Path:
        """Return the dated subdirectory for a specific date.

        Args:
            layer_path: Root path for a specific layer/source combination.
            dt: The date to build the path for.

        Returns:
            Path to the dated subdirectory (not guaranteed to exist).
        """
        return layer_path / dt.strftime("%Y") / dt.strftime("%m") / dt.strftime("%d")

    def list_versions(self, layer_path: Path) -> list[datetime]:
        """Return all version dates found under *layer_path*.

        Scans for directories matching the YYYY/MM/DD pattern and returns
        them as timezone-aware UTC datetimes.

        Args:
            layer_path: Root path for a specific layer/source combination.

        Returns:
            Sorted list of datetimes representing available versions.
        """
        versions: list[datetime] = []

        if not layer_path.exists():
            return versions

        for year_dir in sorted(layer_path.iterdir()):
            if not year_dir.is_dir() or not year_dir.name.isdigit():
                continue
            for month_dir in sorted(year_dir.iterdir()):
                if not month_dir.is_dir() or not month_dir.name.isdigit():
                    continue
                for day_dir in sorted(month_dir.iterdir()):
                    if not day_dir.is_dir() or not day_dir.name.isdigit():
                        continue
                    try:
                        dt = datetime(
                            int(year_dir.name),
                            int(month_dir.name),
                            int(day_dir.name),
                            tzinfo=UTC,
                        )
                        versions.append(dt)
                    except ValueError:
                        continue

        return versions
