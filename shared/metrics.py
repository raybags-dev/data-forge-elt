"""Pipeline metrics tracking for DataForge ELT.

Usage:
    from shared.metrics import PipelineMetricsCollector

    collector = PipelineMetricsCollector()
    metrics = collector.start(pipeline_id="run-001", source="kaggle")
    collector.record_rows_fetched(500)
    collector.record_rows_saved(490)
    collector.add_error("Row 42 failed validation")
    final = collector.finish()
    collector.log_summary(logger)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

from shared.utils import utc_now

if TYPE_CHECKING:
    from loguru import Logger


@dataclass
class PipelineMetrics:
    """Immutable snapshot of a pipeline run's performance metrics.

    Attributes:
        pipeline_id: Unique identifier for the pipeline run.
        source: Data source name (e.g. "kaggle", "scraper").
        started_at: UTC timestamp when the run began.
        ended_at: UTC timestamp when the run finished (None while running).
        rows_fetched: Total rows retrieved from the source.
        rows_processed: Total rows that entered processing logic.
        rows_saved: Total rows written to storage.
        rows_skipped: Total rows intentionally skipped.
        rows_failed: Total rows that failed processing.
        errors: List of error messages encountered.
        warnings: List of warning messages encountered.
        extra: Arbitrary additional metadata.
    """

    pipeline_id: str
    source: str
    started_at: datetime
    ended_at: datetime | None = None
    rows_fetched: int = 0
    rows_processed: int = 0
    rows_saved: int = 0
    rows_skipped: int = 0
    rows_failed: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def duration_seconds(self) -> float | None:
        """Elapsed run time in seconds, or None if the run has not finished."""
        if self.ended_at is None:
            return None
        return (self.ended_at - self.started_at).total_seconds()

    @property
    def success_rate(self) -> float:
        """Fraction of processed rows that were saved (0.0–1.0).

        Returns 0.0 if no rows were processed.
        """
        if self.rows_processed == 0:
            return 0.0
        return self.rows_saved / self.rows_processed


class PipelineMetricsCollector:
    """Mutable collector that accumulates metrics during a pipeline run.

    Create one collector per pipeline execution. Call :meth:`start` first,
    then the ``record_*`` methods as rows flow through, and finally
    :meth:`finish` to capture the end timestamp.
    """

    def __init__(self) -> None:
        self._metrics: PipelineMetrics | None = None

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def start(self, pipeline_id: str, source: str) -> PipelineMetrics:
        """Initialise a new metrics snapshot and begin tracking.

        Args:
            pipeline_id: Unique identifier for this pipeline run.
            source: Data source label.

        Returns:
            The freshly created PipelineMetrics instance.
        """
        self._metrics = PipelineMetrics(
            pipeline_id=pipeline_id,
            source=source,
            started_at=utc_now(),
        )
        return self._metrics

    def finish(self) -> PipelineMetrics:
        """Record the end timestamp and return the final metrics.

        Returns:
            The completed PipelineMetrics snapshot.

        Raises:
            RuntimeError: If :meth:`start` was not called first.
        """
        metrics = self._require_metrics()
        metrics.ended_at = utc_now()
        return metrics

    # ── Row counters ──────────────────────────────────────────────────────────

    def record_rows_fetched(self, n: int) -> None:
        """Increment the fetched row count by *n*."""
        self._require_metrics().rows_fetched += n

    def record_rows_processed(self, n: int) -> None:
        """Increment the processed row count by *n*."""
        self._require_metrics().rows_processed += n

    def record_rows_saved(self, n: int) -> None:
        """Increment the saved row count by *n*."""
        self._require_metrics().rows_saved += n

    def record_rows_skipped(self, n: int) -> None:
        """Increment the skipped row count by *n*."""
        self._require_metrics().rows_skipped += n

    def record_rows_failed(self, n: int) -> None:
        """Increment the failed row count by *n*."""
        self._require_metrics().rows_failed += n

    # ── Diagnostics ───────────────────────────────────────────────────────────

    def add_error(self, msg: str) -> None:
        """Append an error message to the metrics log."""
        self._require_metrics().errors.append(msg)

    def add_warning(self, msg: str) -> None:
        """Append a warning message to the metrics log."""
        self._require_metrics().warnings.append(msg)

    # ── Reporting ─────────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable dict of all metric fields.

        Returns:
            Dictionary with all pipeline metrics, suitable for logging or notification.
        """
        m = self._require_metrics()
        return {
            "pipeline_id": m.pipeline_id,
            "source": m.source,
            "started_at": m.started_at.isoformat(),
            "ended_at": m.ended_at.isoformat() if m.ended_at else None,
            "duration_seconds": m.duration_seconds,
            "rows_fetched": m.rows_fetched,
            "rows_processed": m.rows_processed,
            "rows_saved": m.rows_saved,
            "rows_skipped": m.rows_skipped,
            "rows_failed": m.rows_failed,
            "success_rate": m.success_rate,
            "error_count": len(m.errors),
            "warning_count": len(m.warnings),
            "errors": m.errors,
            "warnings": m.warnings,
            "extra": m.extra,
        }

    def log_summary(self, log: "Logger") -> None:
        """Log all metric fields at INFO level.

        Args:
            log: A Loguru Logger instance.
        """
        m = self._require_metrics()
        log.info(
            "Pipeline summary",
            pipeline_id=m.pipeline_id,
            source=m.source,
            duration_seconds=m.duration_seconds,
            rows_fetched=m.rows_fetched,
            rows_processed=m.rows_processed,
            rows_saved=m.rows_saved,
            rows_skipped=m.rows_skipped,
            rows_failed=m.rows_failed,
            success_rate=round(m.success_rate, 4),
            errors=m.errors,
            warnings=m.warnings,
        )

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _require_metrics(self) -> PipelineMetrics:
        """Return the active metrics or raise if start() was not called."""
        if self._metrics is None:
            raise RuntimeError("PipelineMetricsCollector.start() must be called first.")
        return self._metrics
