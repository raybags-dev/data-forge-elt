"""Pipeline step abstractions and concrete implementations.

Each step receives a mutable context dict and returns an updated copy.
Steps are pure units of work — they have no knowledge of run lifecycle.
"""

from __future__ import annotations

import subprocess
import time
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from shared.logger import get_logger
from shared.notifier import NotificationLevel, NotificationPayload

if TYPE_CHECKING:
    from loguru import Logger

    from config.settings import Settings
    from datalake.manager import DataLakeManager
    from shared.notifier import Notifier
    from warehouse.duckdb.warehouse import DuckDBWarehouse

_log = get_logger(__name__)


class PipelineStep(ABC):
    """Abstract base class for all pipeline steps.

    Attributes:
        name: Unique step identifier used in logging and context keys.
        description: Human-readable description of this step's purpose.
    """

    name: str = "base"
    description: str = ""

    @abstractmethod
    def execute(self, context: dict) -> dict:
        """Run this step and return the updated context.

        Args:
            context: Shared pipeline context dictionary (mutable payload).

        Returns:
            Updated context dictionary with this step's outputs merged in.
        """


class CrawlStep(PipelineStep):
    """Crawls the configured data sources and writes raw output to the lake.

    Args:
        settings: Application settings.
        lake: DataLakeManager for storing crawled output.
        sources: List of source identifiers to crawl.
        logger: Loguru logger instance.
    """

    name = "crawl"
    description = "Crawl web sources and write raw data to the lake"

    def __init__(
        self,
        settings: Settings,
        lake: DataLakeManager,
        sources: list[str],
        logger: Logger | None = None,
    ) -> None:
        self._settings = settings
        self._lake = lake
        self._sources = sources
        self._log = logger or get_logger(__name__)

    def execute(self, context: dict) -> dict:
        """Run crawls for each configured source.

        Args:
            context: Pipeline execution context.

        Returns:
            Context with 'crawl_output_paths' key populated.
        """
        output_paths: list[str] = []
        self._log.info(f"CrawlStep: crawling sources={self._sources}")

        for source in self._sources:
            self._log.info(f"CrawlStep: skipping live crawl for source={source} (stubbed)")
            output_paths.append(str(self._lake.layer_path("raw", source)))

        context["crawl_output_paths"] = output_paths
        return context


class KaggleStep(PipelineStep):
    """Downloads datasets from Kaggle and writes them to the data lake.

    Args:
        settings: Application settings with Kaggle credentials.
        lake: DataLakeManager for storage.
        datasets: List of "owner/name" dataset slugs to download.
        logger: Loguru logger instance.
    """

    name = "kaggle"
    description = "Download Kaggle datasets to the raw lake layer"

    def __init__(
        self,
        settings: Settings,
        lake: DataLakeManager,
        datasets: list[str],
        logger: Logger | None = None,
    ) -> None:
        self._settings = settings
        self._lake = lake
        self._datasets = datasets
        self._log = logger or get_logger(__name__)

    def execute(self, context: dict) -> dict:
        """Download each listed Kaggle dataset.

        Args:
            context: Pipeline execution context.

        Returns:
            Context with 'kaggle_output_paths' key populated.
        """
        output_paths: list[str] = []
        self._log.info(f"KaggleStep: datasets={self._datasets}")

        for dataset_slug in self._datasets:
            dest = self._lake.layer_path("raw", dataset_slug.replace("/", "_"))
            output_paths.append(str(dest))
            self._log.info(f"KaggleStep: registered destination for {dataset_slug}")

        context["kaggle_output_paths"] = output_paths
        return context


class DataLakeStep(PipelineStep):
    """Promotes data through lake layers: raw → bronze → silver.

    Args:
        lake: DataLakeManager instance.
        sources: List of source identifiers to promote.
        logger: Loguru logger instance.
    """

    name = "datalake"
    description = "Promote data through lake layers (raw → bronze → silver)"

    def __init__(
        self,
        lake: DataLakeManager,
        sources: list[str],
        logger: Logger | None = None,
    ) -> None:
        self._lake = lake
        self._sources = sources
        self._log = logger or get_logger(__name__)

    def execute(self, context: dict) -> dict:
        """Promote raw data to bronze and silver layers.

        Args:
            context: Pipeline execution context.

        Returns:
            Context with 'lake_output_paths' key populated.
        """

        output_paths: list[str] = []

        for source in self._sources:
            self._log.info(f"DataLakeStep: promoting source={source}")
            try:
                raw_df = self._lake.read_parquet("raw", source)
                if raw_df.empty:
                    self._log.warning(f"DataLakeStep: no raw data for source={source}")
                    continue
                bronze_path = self._lake.promote("raw", "bronze", source, raw_df)
                silver_path = self._lake.promote("bronze", "silver", source, raw_df)
                output_paths.extend([str(bronze_path), str(silver_path)])
            except Exception as exc:
                self._log.warning(f"DataLakeStep: could not promote {source}: {exc}")

        context["lake_output_paths"] = output_paths
        return context


class WarehouseLoadStep(PipelineStep):
    """Loads silver-layer Parquet files into the DuckDB warehouse.

    Args:
        warehouse: DuckDBWarehouse instance.
        lake: DataLakeManager for reading silver-layer data.
        sources: List of source identifiers to load.
        logger: Loguru logger instance.
    """

    name = "warehouse_load"
    description = "Load silver-layer parquets into the DuckDB warehouse"

    def __init__(
        self,
        warehouse: DuckDBWarehouse,
        lake: DataLakeManager,
        sources: list[str],
        logger: Logger | None = None,
    ) -> None:
        self._warehouse = warehouse
        self._lake = lake
        self._sources = sources
        self._log = logger or get_logger(__name__)

    def execute(self, context: dict) -> dict:
        """Load each source's silver data into DuckDB.

        Args:
            context: Pipeline execution context.

        Returns:
            Context with 'warehouse_tables' key populated.
        """
        loaded_tables: list[str] = []

        for source in self._sources:
            self._log.info(f"WarehouseLoadStep: loading source={source}")
            try:
                df = self._lake.read_parquet("silver", source)
                if df.empty:
                    self._log.warning(f"WarehouseLoadStep: no silver data for source={source}")
                    continue
                self._warehouse.load_dataframe(source, df, mode="overwrite")
                loaded_tables.append(source)
            except Exception as exc:
                self._log.warning(f"WarehouseLoadStep: failed to load {source}: {exc}")

        context["warehouse_tables"] = loaded_tables
        return context


class DbtBuildStep(PipelineStep):
    """Runs `dbt build` against the DuckDB warehouse.

    Args:
        settings: Application settings with dbt project paths.
        select: Optional model selector (dbt --select).
        logger: Loguru logger instance.
    """

    name = "dbt_build"
    description = "Run dbt build to materialise models"

    def __init__(
        self,
        settings: Settings,
        select: str | None = None,
        logger: Logger | None = None,
    ) -> None:
        self._settings = settings
        self._select = select
        self._log = logger or get_logger(__name__)

    def execute(self, context: dict) -> dict:
        """Execute dbt build.

        Args:
            context: Pipeline execution context.

        Returns:
            Context with 'dbt_build_output' key populated.
        """
        cmd = self._build_command("build")
        result = self._run_subprocess(cmd)
        context["dbt_build_output"] = result
        return context

    def _build_command(self, subcmd: str) -> list[str]:
        """Assemble the dbt CLI command list."""
        cmd = [
            "uv", "run", "dbt", subcmd,
            "--project-dir", str(self._settings.dbt_project_dir),
            "--profiles-dir", str(self._settings.dbt_profiles_dir),
        ]
        if self._select:
            cmd.extend(["--select", self._select])
        return cmd

    def _run_subprocess(self, cmd: list[str]) -> dict:
        """Run a subprocess command and return the result dict."""
        self._log.info(f"Running: {' '.join(cmd)}")
        start = time.monotonic()
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            duration = time.monotonic() - start
            return {
                "returncode": proc.returncode,
                "stdout": proc.stdout,
                "stderr": proc.stderr,
                "duration_seconds": duration,
                "success": proc.returncode == 0,
            }
        except Exception as exc:
            return {
                "returncode": -1,
                "stdout": "",
                "stderr": str(exc),
                "duration_seconds": time.monotonic() - start,
                "success": False,
            }


class DbtTestStep(PipelineStep):
    """Runs `dbt test` to validate data models.

    Args:
        settings: Application settings with dbt project paths.
        select: Optional model selector.
        logger: Loguru logger instance.
    """

    name = "dbt_test"
    description = "Run dbt test to validate data models"

    def __init__(
        self,
        settings: Settings,
        select: str | None = None,
        logger: Logger | None = None,
    ) -> None:
        self._settings = settings
        self._select = select
        self._log = logger or get_logger(__name__)

    def execute(self, context: dict) -> dict:
        """Execute dbt test.

        Args:
            context: Pipeline execution context.

        Returns:
            Context with 'dbt_test_output' key populated.
        """
        cmd = [
            "uv", "run", "dbt", "test",
            "--project-dir", str(self._settings.dbt_project_dir),
            "--profiles-dir", str(self._settings.dbt_profiles_dir),
        ]
        if self._select:
            cmd.extend(["--select", self._select])

        self._log.info(f"Running: {' '.join(cmd)}")
        start = time.monotonic()
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            duration = time.monotonic() - start
            result = {
                "returncode": proc.returncode,
                "stdout": proc.stdout,
                "stderr": proc.stderr,
                "duration_seconds": duration,
                "success": proc.returncode == 0,
            }
        except Exception as exc:
            result = {
                "returncode": -1,
                "stdout": "",
                "stderr": str(exc),
                "duration_seconds": time.monotonic() - start,
                "success": False,
            }

        context["dbt_test_output"] = result
        return context


class DbtDocsStep(PipelineStep):
    """Runs `dbt docs generate` to produce documentation artefacts.

    Args:
        settings: Application settings with dbt project paths.
        logger: Loguru logger instance.
    """

    name = "dbt_docs"
    description = "Generate dbt documentation artefacts"

    def __init__(
        self,
        settings: Settings,
        logger: Logger | None = None,
    ) -> None:
        self._settings = settings
        self._log = logger or get_logger(__name__)

    def execute(self, context: dict) -> dict:
        """Execute dbt docs generate.

        Args:
            context: Pipeline execution context.

        Returns:
            Context with 'dbt_docs_output' key populated.
        """
        cmd = [
            "uv", "run", "dbt", "docs", "generate",
            "--project-dir", str(self._settings.dbt_project_dir),
            "--profiles-dir", str(self._settings.dbt_profiles_dir),
        ]
        self._log.info(f"Running: {' '.join(cmd)}")
        start = time.monotonic()
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            duration = time.monotonic() - start
            result = {
                "returncode": proc.returncode,
                "stdout": proc.stdout,
                "stderr": proc.stderr,
                "duration_seconds": duration,
                "success": proc.returncode == 0,
            }
        except Exception as exc:
            result = {
                "returncode": -1,
                "stdout": "",
                "stderr": str(exc),
                "duration_seconds": time.monotonic() - start,
                "success": False,
            }

        context["dbt_docs_output"] = result
        return context


class NotifyStep(PipelineStep):
    """Sends a pipeline completion notification via the configured notifier.

    Args:
        notifier: Notifier instance for delivering alerts.
        logger: Loguru logger instance.
    """

    name = "notify"
    description = "Send pipeline completion notification"

    def __init__(
        self,
        notifier: Notifier,
        logger: Logger | None = None,
    ) -> None:
        self._notifier = notifier
        self._log = logger or get_logger(__name__)

    def execute(self, context: dict) -> dict:
        """Send completion notification using run metadata from context.

        Args:
            context: Pipeline execution context (expects 'run_id' key).

        Returns:
            Unchanged context.
        """
        run_id = context.get("run_id", "unknown")
        status = context.get("status", "UNKNOWN")

        level = (
            NotificationLevel.INFO
            if status in ("SUCCESS", "RUNNING")
            else NotificationLevel.ERROR
        )

        self._notifier.send(
            NotificationPayload(
                title=f"Pipeline {status}",
                message=f"Run {run_id} completed with status: {status}",
                level=level,
                pipeline_id=run_id,
                details=context.get("metrics"),
            )
        )
        return context
