"""PipelineScheduler — cron-based pipeline scheduling via APScheduler."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from shared.logger import get_logger

if TYPE_CHECKING:
    from orchestration.models import PipelineConfig
    from orchestration.pipeline import PipelineOrchestrator

_log = get_logger(__name__)


class PipelineScheduler:
    """Schedules pipelines on cron expressions using APScheduler.

    Uses AsyncIOScheduler so it can run inside an asyncio event loop
    alongside a FastAPI application.

    Args:
        orchestrator: PipelineOrchestrator used to execute scheduled runs.
    """

    def __init__(self, orchestrator: "PipelineOrchestrator") -> None:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler

        self._orchestrator = orchestrator
        self._scheduler = AsyncIOScheduler()
        self._log = get_logger(__name__)

    def start(self) -> None:
        """Start the APScheduler background scheduler."""
        if not self._scheduler.running:
            self._scheduler.start()
            self._log.info("PipelineScheduler started")

    def stop(self) -> None:
        """Shut down the APScheduler gracefully."""
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)
            self._log.info("PipelineScheduler stopped")

    def schedule_pipeline(
        self, config: "PipelineConfig", cron_expr: str
    ) -> str:
        """Add a cron-triggered pipeline job.

        Args:
            config: PipelineConfig to execute on each trigger.
            cron_expr: Standard 5-field cron expression (e.g. "0 * * * *").

        Returns:
            APScheduler job_id string that can be used to cancel the job.
        """
        job_id = str(uuid.uuid4())
        fields = self._parse_cron(cron_expr)

        self._scheduler.add_job(
            self._run_pipeline,
            trigger="cron",
            id=job_id,
            args=[config],
            **fields,
        )
        self._log.info(
            f"Scheduled pipeline '{config.pipeline_id}' with cron='{cron_expr}' job_id={job_id}"
        )
        return job_id

    def cancel_job(self, job_id: str) -> bool:
        """Remove a scheduled job by its job_id.

        Args:
            job_id: The identifier returned by :meth:`schedule_pipeline`.

        Returns:
            True if the job was found and removed, False otherwise.
        """
        try:
            self._scheduler.remove_job(job_id)
            self._log.info(f"Cancelled scheduled job {job_id}")
            return True
        except Exception:
            return False

    def list_jobs(self) -> list[dict[str, Any]]:
        """Return metadata for all currently scheduled jobs.

        Returns:
            List of dicts with id, name, next_run_time fields.
        """
        jobs = self._scheduler.get_jobs()
        return [
            {
                "job_id": job.id,
                "name": job.name,
                "next_run_time": (
                    job.next_run_time.isoformat() if job.next_run_time else None
                ),
                "trigger": str(job.trigger),
            }
            for job in jobs
        ]

    def _run_pipeline(self, config: "PipelineConfig") -> None:
        """Callback invoked by APScheduler on each cron trigger.

        Args:
            config: PipelineConfig to execute.
        """
        self._log.info(f"Scheduler triggered pipeline '{config.pipeline_id}'")
        try:
            self._orchestrator.run(config)
        except Exception as exc:
            self._log.error(f"Scheduled pipeline '{config.pipeline_id}' failed: {exc}")

    @staticmethod
    def _parse_cron(cron_expr: str) -> dict[str, str]:
        """Parse a 5-field cron expression into APScheduler keyword arguments.

        Args:
            cron_expr: "minute hour day month day_of_week" string.

        Returns:
            Dict with keys: minute, hour, day, month, day_of_week.
        """
        parts = cron_expr.strip().split()
        if len(parts) != 5:
            raise ValueError(
                f"Expected 5-field cron expression, got {len(parts)} fields: '{cron_expr}'"
            )
        keys = ["minute", "hour", "day", "month", "day_of_week"]
        return dict(zip(keys, parts))
