"""PipelineOrchestrator — executes pipeline configs end-to-end."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from shared.logger import get_logger, pipeline_context
from shared.metrics import PipelineMetrics, PipelineMetricsCollector
from shared.notifier import NotificationLevel, NotificationPayload

from orchestration.models import PipelineConfig, PipelineRun, PipelineStatus

if TYPE_CHECKING:
    from loguru import Logger

    from config.settings import Settings
    from datalake.manager import DataLakeManager
    from shared.notifier import Notifier
    from warehouse.duckdb.warehouse import DuckDBWarehouse


class PipelineOrchestrator:
    """Executes pipeline configurations by running their steps in order.

    Maintains an in-memory registry of all completed and in-flight runs.
    Steps are resolved from the provided step instances passed at call time
    or from the default step builder.

    Args:
        warehouse: DuckDB warehouse for WarehouseLoadStep.
        lake: DataLakeManager for lake-layer steps.
        notifier: Notifier for success/failure alerts.
        settings: Application settings.
        logger: Loguru logger instance.
    """

    def __init__(
        self,
        warehouse: "DuckDBWarehouse",
        lake: "DataLakeManager",
        notifier: "Notifier",
        settings: "Settings",
        logger: "Logger | None" = None,
    ) -> None:
        self._warehouse = warehouse
        self._lake = lake
        self._notifier = notifier
        self._settings = settings
        self._log = logger or get_logger(__name__)
        self._runs: dict[str, PipelineRun] = {}

    def run(self, config: PipelineConfig) -> PipelineRun:
        """Execute all steps in a PipelineConfig and return the run record.

        Steps execute in ascending `order` value. On any failure the run is
        marked FAILED, a notification is dispatched, and execution stops.

        Args:
            config: Static pipeline configuration describing the steps.

        Returns:
            Completed PipelineRun with final status and metrics.
        """
        run = self._create_run(config)
        self._runs[run.run_id] = run

        with pipeline_context(pipeline_id=run.run_id):
            self._log.info(f"Pipeline '{config.name}' started (run_id={run.run_id})")
            collector = PipelineMetricsCollector()
            collector.start(pipeline_id=run.run_id, source=",".join(config.sources))
            context: dict = {"run_id": run.run_id, "config": config}

            sorted_steps = sorted(config.steps, key=lambda s: s.order)
            steps = self._build_steps(config)

            for step_model in sorted_steps:
                step = steps.get(step_model.name)
                if step is None:
                    self._log.warning(f"No implementation for step '{step_model.name}', skipping")
                    continue

                if run.status == PipelineStatus.CANCELLED:
                    break

                context = self._execute_step(run, step, context)
                if run.status == PipelineStatus.FAILED:
                    break

            metrics = collector.finish()
            self._finalise_run(run, context, metrics)
            self._log.info(
                f"Pipeline '{config.name}' finished "
                f"status={run.status} duration={run.duration_seconds:.2f}s"
            )

        return run

    def get_run(self, run_id: str) -> PipelineRun | None:
        """Return the PipelineRun for *run_id*, or None if not found.

        Args:
            run_id: The run identifier to look up.
        """
        return self._runs.get(run_id)

    def list_runs(self) -> list[PipelineRun]:
        """Return all stored pipeline runs in insertion order.

        Returns:
            List of PipelineRun instances.
        """
        return list(self._runs.values())

    def cancel_run(self, run_id: str) -> bool:
        """Mark a run as CANCELLED if it is currently RUNNING or PENDING.

        Args:
            run_id: The run identifier to cancel.

        Returns:
            True if the run was cancelled, False if not found or not cancellable.
        """
        run = self._runs.get(run_id)
        if run is None:
            return False
        if run.status not in (PipelineStatus.RUNNING, PipelineStatus.PENDING):
            return False
        run.status = PipelineStatus.CANCELLED
        run.ended_at = datetime.now(tz=timezone.utc)
        self._log.info(f"Run {run_id} cancelled")
        return True

    def _create_run(self, config: PipelineConfig) -> PipelineRun:
        """Build a fresh PipelineRun in RUNNING state."""
        return PipelineRun(
            run_id=str(uuid.uuid4()),
            config=config,
            status=PipelineStatus.RUNNING,
            started_at=datetime.now(tz=timezone.utc),
        )

    def _build_steps(self, config: PipelineConfig) -> dict:
        """Instantiate the concrete step objects for this config."""
        from orchestration.steps import (
            CrawlStep,
            DataLakeStep,
            DbtBuildStep,
            DbtDocsStep,
            DbtTestStep,
            KaggleStep,
            NotifyStep,
            WarehouseLoadStep,
        )

        return {
            "crawl": CrawlStep(self._settings, self._lake, config.sources, self._log),
            "kaggle": KaggleStep(self._settings, self._lake, config.sources, self._log),
            "datalake": DataLakeStep(self._lake, config.sources, self._log),
            "warehouse_load": WarehouseLoadStep(
                self._warehouse, self._lake, config.sources, self._log
            ),
            "dbt_build": DbtBuildStep(self._settings, logger=self._log),
            "dbt_test": DbtTestStep(self._settings, logger=self._log),
            "dbt_docs": DbtDocsStep(self._settings, logger=self._log),
            "notify": NotifyStep(self._notifier, logger=self._log),
        }

    def _execute_step(self, run: PipelineRun, step, context: dict) -> dict:
        """Run a single step and handle any exceptions.

        Args:
            run: Active PipelineRun (mutated on failure).
            step: The step instance to execute.
            context: Current pipeline context dict.

        Returns:
            Updated context if step succeeded; original context on failure.
        """
        self._log.info(f"Executing step: {step.name}")
        try:
            return step.execute(context)
        except Exception as exc:
            msg = f"Step '{step.name}' failed: {exc}"
            self._log.error(msg)
            run.errors.append(msg)
            run.status = PipelineStatus.FAILED
            return context

    def _finalise_run(
        self, run: PipelineRun, context: dict, metrics: PipelineMetrics
    ) -> None:
        """Set end state and send notification for a completed run.

        Args:
            run: The PipelineRun being finalised.
            context: Final pipeline context.
            metrics: Completed metrics snapshot.
        """
        run.ended_at = datetime.now(tz=timezone.utc)
        run.metrics = metrics

        if run.status == PipelineStatus.RUNNING:
            run.status = PipelineStatus.SUCCESS

        output_paths = []
        for key in ("crawl_output_paths", "kaggle_output_paths", "lake_output_paths"):
            output_paths.extend(context.get(key, []))
        run.output_paths = output_paths

        level = (
            NotificationLevel.INFO
            if run.status == PipelineStatus.SUCCESS
            else NotificationLevel.ERROR
        )
        self._notifier.send(
            NotificationPayload(
                title=f"Pipeline {run.status.value}",
                message=(
                    f"Run '{run.config.name}' finished in "
                    f"{run.duration_seconds:.2f}s"
                ),
                level=level,
                pipeline_id=run.run_id,
                details={"status": run.status.value, "errors": run.errors},
            )
        )
