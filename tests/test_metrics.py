"""Tests for shared.metrics."""

from __future__ import annotations

import pytest

from shared.metrics import PipelineMetricsCollector


def test_metrics_start_sets_started_at() -> None:
    """start() should record a non-None started_at datetime."""
    collector = PipelineMetricsCollector()
    metrics = collector.start(pipeline_id="run-001", source="kaggle")
    assert metrics.started_at is not None
    assert metrics.pipeline_id == "run-001"
    assert metrics.source == "kaggle"


def test_metrics_finish_sets_ended_at() -> None:
    """finish() should set ended_at to a non-None datetime."""
    collector = PipelineMetricsCollector()
    collector.start(pipeline_id="run-002", source="scraper")
    metrics = collector.finish()
    assert metrics.ended_at is not None


def test_metrics_duration_seconds() -> None:
    """duration_seconds should be a positive float after finish()."""
    collector = PipelineMetricsCollector()
    collector.start(pipeline_id="run-003", source="api")
    metrics = collector.finish()
    assert metrics.duration_seconds is not None
    assert metrics.duration_seconds >= 0.0


def test_metrics_to_dict_has_all_fields() -> None:
    """to_dict() should include all standard metric keys."""
    collector = PipelineMetricsCollector()
    collector.start(pipeline_id="run-004", source="csv")
    collector.record_rows_fetched(100)
    collector.record_rows_processed(95)
    collector.record_rows_saved(90)
    collector.record_rows_skipped(5)
    collector.record_rows_failed(0)
    collector.add_error("something went wrong")
    collector.add_warning("skipped 5 rows")
    collector.finish()

    d = collector.to_dict()
    expected_keys = {
        "pipeline_id", "source", "started_at", "ended_at", "duration_seconds",
        "rows_fetched", "rows_processed", "rows_saved", "rows_skipped",
        "rows_failed", "success_rate", "error_count", "warning_count",
        "errors", "warnings", "extra",
    }
    assert expected_keys.issubset(d.keys())
    assert d["rows_fetched"] == 100
    assert d["rows_processed"] == 95
    assert d["rows_saved"] == 90
    assert d["error_count"] == 1
    assert d["warning_count"] == 1


def test_metrics_success_rate() -> None:
    """success_rate should be rows_saved / rows_processed."""
    collector = PipelineMetricsCollector()
    collector.start("run-005", "test")
    collector.record_rows_processed(200)
    collector.record_rows_saved(180)
    metrics = collector.finish()
    assert metrics.success_rate == pytest.approx(0.9)


def test_metrics_start_required_before_finish() -> None:
    """finish() without start() should raise RuntimeError."""
    collector = PipelineMetricsCollector()
    with pytest.raises(RuntimeError):
        collector.finish()
