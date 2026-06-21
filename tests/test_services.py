"""Tests for the app/services layer."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ── DbtService tests ───────────────────────────────────────────────────────────


def test_dbt_service_build_command_format(tmp_settings) -> None:
    """DbtService.build() must call subprocess with correct dbt CLI arguments."""
    from app.services.dbt_service import DbtService

    service = DbtService(settings=tmp_settings)

    expected_prefix = ["uv", "run", "dbt", "build"]
    base_cmd = service._base_command("build")

    assert base_cmd[:4] == expected_prefix
    assert "--project-dir" in base_cmd
    assert "--profiles-dir" in base_cmd


def test_dbt_service_test_command_format(tmp_settings) -> None:
    """DbtService._base_command('test') must produce a valid test command."""
    from app.services.dbt_service import DbtService

    service = DbtService(settings=tmp_settings)
    cmd = service._base_command("test")

    assert cmd[2] == "dbt"
    assert cmd[3] == "test"


def test_dbt_service_parse_model_count_empty() -> None:
    """_parse_model_count with empty output should return 0."""
    from app.services.dbt_service import DbtService

    assert DbtService._parse_model_count("") == 0
    assert DbtService._parse_model_count("No models found") == 0


def test_dbt_service_parse_model_count_with_ok_pattern() -> None:
    """_parse_model_count should extract the highest model number from output."""
    from app.services.dbt_service import DbtService

    output = "1 of 3 OK\n2 of 3 OK\n3 of 3 OK\nDone. PASS=3 WARN=0 ERROR=0"
    count = DbtService._parse_model_count(output)
    assert count == 3


@pytest.mark.asyncio
async def test_dbt_service_build_runs_subprocess(tmp_settings) -> None:
    """DbtService.build() should invoke subprocess.run and return DbtBuildResponse."""
    import subprocess

    from app.services.dbt_service import DbtService

    service = DbtService(settings=tmp_settings)

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "Done. PASS=2"
    mock_result.stderr = ""

    with patch("subprocess.run", return_value=mock_result) as mock_run:
        resp = await service.build(select=None)

    assert resp.success is True
    assert mock_run.called
    call_args = mock_run.call_args[0][0]
    assert "dbt" in call_args
    assert "build" in call_args


@pytest.mark.asyncio
async def test_dbt_service_build_with_select(tmp_settings) -> None:
    """DbtService.build(select='tag:daily') must include --select in the command."""
    from app.services.dbt_service import DbtService

    service = DbtService(settings=tmp_settings)

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = ""
    mock_result.stderr = ""

    with patch("subprocess.run", return_value=mock_result) as mock_run:
        await service.build(select="tag:daily")

    call_args = mock_run.call_args[0][0]
    assert "--select" in call_args
    assert "tag:daily" in call_args


@pytest.mark.asyncio
async def test_dbt_service_handles_subprocess_exception(tmp_settings) -> None:
    """DbtService.build() should return success=False when subprocess raises."""
    from app.services.dbt_service import DbtService

    service = DbtService(settings=tmp_settings)

    with patch("subprocess.run", side_effect=FileNotFoundError("dbt not found")):
        resp = await service.build()

    assert resp.success is False
    assert "dbt not found" in resp.output


# ── DatasetService tests ───────────────────────────────────────────────────────


def test_dataset_service_list_empty_lake(tmp_path) -> None:
    """DatasetService.list_datasets() must return empty list when lake has no files."""
    from datalake.manager import DataLakeManager
    from shared.logger import get_logger

    from app.services.dataset_service import DatasetService

    lake = DataLakeManager(base_path=tmp_path / "datalake", logger=get_logger("test"))
    lake.setup()

    service = DatasetService(lake=lake)
    result = service.list_datasets()

    assert result.datasets == []
    assert result.total == 0


def test_dataset_service_list_with_parquet(tmp_path) -> None:
    """DatasetService.list_datasets() must return one item when a parquet exists."""
    import pandas as pd

    from datalake.manager import DataLakeManager
    from shared.logger import get_logger

    from app.services.dataset_service import DatasetService

    lake = DataLakeManager(base_path=tmp_path / "datalake", logger=get_logger("test"))
    lake.setup()

    df = pd.DataFrame({"col1": [1, 2, 3], "col2": ["a", "b", "c"]})
    lake.write_parquet("raw", "test_source", df, filename="data.parquet")

    service = DatasetService(lake=lake)
    result = service.list_datasets()

    assert result.total == 1
    assert result.datasets[0].source == "test_source"
    assert result.datasets[0].layer == "raw"


def test_dataset_service_get_preview_not_found(tmp_path) -> None:
    """DatasetService.get_preview() returns empty list for non-existent datasets."""
    from datalake.manager import DataLakeManager
    from shared.logger import get_logger

    from app.services.dataset_service import DatasetService

    lake = DataLakeManager(base_path=tmp_path / "datalake", logger=get_logger("test"))
    lake.setup()

    service = DatasetService(lake=lake)
    result = service.get_preview(source="nonexistent", name="file.parquet")

    assert result == []


def test_dataset_service_get_preview_returns_rows(tmp_path) -> None:
    """DatasetService.get_preview() returns up to 100 rows from a matching file."""
    import pandas as pd

    from datalake.manager import DataLakeManager
    from shared.logger import get_logger

    from app.services.dataset_service import DatasetService

    lake = DataLakeManager(base_path=tmp_path / "datalake", logger=get_logger("test"))
    lake.setup()

    df = pd.DataFrame({"id": list(range(200)), "val": list(range(200))})
    lake.write_parquet("raw", "preview_source", df, filename="preview.parquet")

    service = DatasetService(lake=lake)
    rows = service.get_preview(source="preview_source", name="preview.parquet")

    assert len(rows) <= 100
    assert len(rows) > 0


# ── CrawlService tests ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_crawl_service_returns_response(tmp_path, tmp_settings) -> None:
    """CrawlService.run_crawl() must return a CrawlResponse with a run_id."""
    from datalake.manager import DataLakeManager
    from shared.logger import get_logger
    from shared.notifier import NotifierFactory

    from app.services.crawl_service import CrawlService

    lake = DataLakeManager(base_path=tmp_path / "datalake", logger=get_logger("test"))
    lake.setup()
    notifier = NotifierFactory.build_notifier(tmp_settings)
    service = CrawlService(settings=tmp_settings, notifier=notifier, lake=lake)

    result = await service.run_crawl(
        source="test_source",
        urls=["https://example.com"],
        output_name=None,
    )

    assert result.run_id != ""
    assert result.status in ("queued", "error")


# ── PipelineService tests ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_pipeline_service_get_status_not_found(tmp_settings) -> None:
    """PipelineService.get_status() returns None for unknown run_id."""
    from orchestration.pipeline import PipelineOrchestrator
    from shared.logger import get_logger

    from app.services.pipeline_service import PipelineService

    mock_warehouse = MagicMock()
    mock_lake = MagicMock()
    mock_lake.LAYERS = ["raw", "bronze", "silver", "gold"]
    mock_notifier = MagicMock()

    orchestrator = PipelineOrchestrator(
        warehouse=mock_warehouse,
        lake=mock_lake,
        notifier=mock_notifier,
        settings=tmp_settings,
        logger=get_logger("test"),
    )

    service = PipelineService(orchestrator=orchestrator)
    result = await service.get_status("unknown-run-id")
    assert result is None


@pytest.mark.asyncio
async def test_pipeline_service_list_runs_empty(tmp_settings) -> None:
    """PipelineService.list_runs() returns empty list when no runs have been executed."""
    from orchestration.pipeline import PipelineOrchestrator
    from shared.logger import get_logger

    from app.services.pipeline_service import PipelineService

    mock_warehouse = MagicMock()
    mock_lake = MagicMock()
    mock_lake.LAYERS = ["raw", "bronze", "silver", "gold"]
    mock_notifier = MagicMock()

    orchestrator = PipelineOrchestrator(
        warehouse=mock_warehouse,
        lake=mock_lake,
        notifier=mock_notifier,
        settings=tmp_settings,
        logger=get_logger("test"),
    )

    service = PipelineService(orchestrator=orchestrator)
    result = await service.list_runs()
    assert result == []
