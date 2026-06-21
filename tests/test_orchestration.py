"""Tests for orchestration layer: models, pipeline, and scheduler."""

from __future__ import annotations

from datetime import UTC
from unittest.mock import MagicMock

import pytest

from orchestration.models import (
    PipelineConfig,
    PipelineRun,
    PipelineStatus,
    PipelineStepModel,
)
from orchestration.pipeline import PipelineOrchestrator

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture()
def simple_config() -> PipelineConfig:
    """A minimal PipelineConfig with one no-op step."""
    return PipelineConfig(
        pipeline_id="test-pipeline",
        name="Test Pipeline",
        description="Integration test pipeline",
        steps=[PipelineStepModel(name="notify", order=1)],
        sources=["test_source"],
    )


@pytest.fixture()
def mock_warehouse() -> MagicMock:
    """Mock DuckDBWarehouse."""
    return MagicMock()


@pytest.fixture()
def mock_lake(tmp_path) -> MagicMock:
    """Mock DataLakeManager."""
    lake = MagicMock()
    lake.LAYERS = ["raw", "bronze", "silver", "gold"]
    lake.layer_path.return_value = tmp_path / "raw" / "test_source"
    lake.list_entries.return_value = []
    return lake


@pytest.fixture()
def mock_notifier() -> MagicMock:
    """Mock Notifier that records calls."""
    return MagicMock()


@pytest.fixture()
def orchestrator(mock_warehouse, mock_lake, mock_notifier, tmp_settings):
    """A fully wired PipelineOrchestrator using mocked collaborators."""
    from shared.logger import get_logger

    return PipelineOrchestrator(
        warehouse=mock_warehouse,
        lake=mock_lake,
        notifier=mock_notifier,
        settings=tmp_settings,
        logger=get_logger("test"),
    )


# ── Tests ─────────────────────────────────────────────────────────────────────


def test_pipeline_status_enum_values() -> None:
    """All five expected PipelineStatus values must be defined."""
    assert PipelineStatus.PENDING == "PENDING"
    assert PipelineStatus.RUNNING == "RUNNING"
    assert PipelineStatus.SUCCESS == "SUCCESS"
    assert PipelineStatus.FAILED == "FAILED"
    assert PipelineStatus.CANCELLED == "CANCELLED"


def test_pipeline_run_has_duration_property() -> None:
    """PipelineRun.duration_seconds should return None before completion."""
    config = PipelineConfig(pipeline_id="p1", name="P1")
    run = PipelineRun(run_id="r1", config=config)
    assert run.duration_seconds is None


def test_pipeline_run_creates_run(orchestrator, simple_config) -> None:
    """orchestrator.run() must return a PipelineRun with a run_id."""
    run = orchestrator.run(simple_config)

    assert run is not None
    assert isinstance(run, PipelineRun)
    assert run.run_id != ""
    assert run.config.pipeline_id == simple_config.pipeline_id


def test_pipeline_run_ends_in_terminal_state(orchestrator, simple_config) -> None:
    """A completed run must be in SUCCESS or FAILED state, never RUNNING."""
    run = orchestrator.run(simple_config)

    assert run.status in (PipelineStatus.SUCCESS, PipelineStatus.FAILED)


def test_pipeline_run_stored_in_memory(orchestrator, simple_config) -> None:
    """The run must be retrievable via get_run() after completion."""
    run = orchestrator.run(simple_config)

    retrieved = orchestrator.get_run(run.run_id)
    assert retrieved is not None
    assert retrieved.run_id == run.run_id


def test_pipeline_list_runs_includes_completed(orchestrator, simple_config) -> None:
    """list_runs() must include all runs that have been executed."""
    run = orchestrator.run(simple_config)
    all_runs = orchestrator.list_runs()

    run_ids = [r.run_id for r in all_runs]
    assert run.run_id in run_ids


def test_pipeline_cancel_run(orchestrator, simple_config) -> None:
    """cancel_run() on an unknown id returns False; on a known PENDING id returns True."""
    assert orchestrator.cancel_run("nonexistent-id") is False

    # Manually insert a PENDING run
    from datetime import datetime

    pending_run = PipelineRun(
        run_id="pending-001",
        config=simple_config,
        status=PipelineStatus.PENDING,
        started_at=datetime.now(tz=UTC),
    )
    orchestrator._runs["pending-001"] = pending_run
    assert orchestrator.cancel_run("pending-001") is True
    assert orchestrator._runs["pending-001"].status == PipelineStatus.CANCELLED


def test_get_run_returns_none_for_unknown(orchestrator) -> None:
    """get_run() with a non-existent id must return None."""
    assert orchestrator.get_run("does-not-exist") is None


@pytest.mark.asyncio
async def test_scheduler_creates_and_cancels_job(orchestrator) -> None:
    """schedule_pipeline() returns a job_id; cancel_job() removes it."""
    from orchestration.scheduler import PipelineScheduler

    scheduler = PipelineScheduler(orchestrator=orchestrator)
    scheduler.start()

    try:
        config = PipelineConfig(pipeline_id="sched-test", name="Scheduled")
        job_id = scheduler.schedule_pipeline(config, cron_expr="0 * * * *")

        assert isinstance(job_id, str)
        assert len(job_id) > 0

        jobs = scheduler.list_jobs()
        job_ids = [j["job_id"] for j in jobs]
        assert job_id in job_ids

        result = scheduler.cancel_job(job_id)
        assert result is True

        jobs_after = scheduler.list_jobs()
        job_ids_after = [j["job_id"] for j in jobs_after]
        assert job_id not in job_ids_after
    finally:
        scheduler.stop()


@pytest.mark.asyncio
async def test_scheduler_cancel_unknown_job(orchestrator) -> None:
    """cancel_job() with a non-existent id must return False."""
    from orchestration.scheduler import PipelineScheduler

    scheduler = PipelineScheduler(orchestrator=orchestrator)
    scheduler.start()
    try:
        assert scheduler.cancel_job("nonexistent-job-999") is False
    finally:
        scheduler.stop()


@pytest.mark.asyncio
async def test_scheduler_parses_invalid_cron(orchestrator) -> None:
    """schedule_pipeline() raises ValueError for malformed cron expressions."""
    from orchestration.scheduler import PipelineScheduler

    scheduler = PipelineScheduler(orchestrator=orchestrator)
    scheduler.start()
    try:
        config = PipelineConfig(pipeline_id="bad-cron", name="Bad")
        with pytest.raises(ValueError):
            scheduler.schedule_pipeline(config, cron_expr="bad-cron")
    finally:
        scheduler.stop()
