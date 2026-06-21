"""Tests for the FastAPI application endpoints."""

from __future__ import annotations

from pathlib import Path
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import create_app


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def anyio_backend():
    """Use asyncio for all async tests in this module."""
    return "asyncio"


@pytest.fixture()
def app(tmp_path):
    """Create a test FastAPI app with all DI overrides applied."""
    from app.dependencies import (
        get_crawl_service,
        get_dataset_service,
        get_dbt_service,
        get_kaggle_service,
        get_orchestrator,
        get_pipeline_service,
        get_settings_dep,
    )
    from config.settings import Settings

    test_app = create_app()

    # Override settings to use tmp_path
    test_settings = Settings(
        APP_NAME="TestForge",
        LOG_DIR=str(tmp_path / "logs"),
        DATA_LAKE=str(tmp_path / "datalake"),
        DUCKDB_PATH=str(tmp_path / "warehouse" / "test.duckdb"),
        DBT_PROJECT_DIR=str(tmp_path / "dbt"),
        DBT_PROFILES_DIR=str(tmp_path / "dbt"),
    )

    # Build a mock orchestrator
    mock_orchestrator = _build_mock_orchestrator()

    # Build mock services
    mock_pipeline_service = _build_mock_pipeline_service()
    mock_crawl_service = _build_mock_crawl_service()
    mock_dataset_service = _build_mock_dataset_service()
    mock_dbt_service = _build_mock_dbt_service()
    mock_kaggle_service = _build_mock_kaggle_service()

    test_app.dependency_overrides[get_settings_dep] = lambda: test_settings
    test_app.dependency_overrides[get_orchestrator] = lambda: mock_orchestrator
    test_app.dependency_overrides[get_pipeline_service] = lambda: mock_pipeline_service
    test_app.dependency_overrides[get_crawl_service] = lambda: mock_crawl_service
    test_app.dependency_overrides[get_dataset_service] = lambda: mock_dataset_service
    test_app.dependency_overrides[get_dbt_service] = lambda: mock_dbt_service
    test_app.dependency_overrides[get_kaggle_service] = lambda: mock_kaggle_service

    return test_app


@pytest_asyncio.fixture()
async def client(app) -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP client wired to the test app via ASGI transport."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


# ── Mock helpers ──────────────────────────────────────────────────────────────


def _build_mock_orchestrator():
    m = MagicMock()
    m.list_runs.return_value = []
    m.get_run.return_value = None
    return m


def _build_mock_pipeline_service():
    from app.api.schemas.pipeline import PipelineRunResponse, PipelineStatusResponse

    svc = MagicMock()
    svc.run_pipeline = AsyncMock(
        return_value=PipelineRunResponse(
            run_id="run-001",
            pipeline_id="test",
            status="SUCCESS",
        )
    )
    svc.get_status = AsyncMock(return_value=None)
    svc.list_runs = AsyncMock(return_value=[])
    svc.cancel_run = AsyncMock(return_value=False)
    return svc


def _build_mock_crawl_service():
    from app.api.schemas.crawl import CrawlResponse

    svc = MagicMock()
    svc.run_crawl = AsyncMock(
        return_value=CrawlResponse(
            run_id="crawl-001",
            status="queued",
            message="Queued",
            output_path="/tmp/raw/test",
        )
    )
    return svc


def _build_mock_dataset_service():
    from app.api.schemas.datasets import DatasetListResponse

    svc = MagicMock()
    svc.list_datasets.return_value = DatasetListResponse(datasets=[], total=0)
    svc.get_preview.return_value = []
    return svc


def _build_mock_dbt_service():
    from app.api.schemas.dbt import DbtBuildResponse

    svc = MagicMock()
    resp = DbtBuildResponse(success=True, output="OK", duration_seconds=1.0, models_run=2)
    svc.build = AsyncMock(return_value=resp)
    svc.test = AsyncMock(return_value=resp)
    svc.docs_generate = AsyncMock(return_value=resp)
    return svc


def _build_mock_kaggle_service():
    from app.api.schemas.kaggle import KaggleDownloadResponse

    svc = MagicMock()
    svc.download = AsyncMock(
        return_value=KaggleDownloadResponse(
            dataset_name="owner/ds",
            parquet_files=[],
            rows_total=0,
            duration_seconds=1.0,
            success=True,
        )
    )
    return svc


# ── Tests ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient) -> None:
    """GET /health must return 200 with status='ok'."""
    response = await client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "version" in body


@pytest.mark.asyncio
async def test_crawl_endpoint_validates_request(client: AsyncClient) -> None:
    """POST /api/v1/crawl with missing required fields must return 422."""
    response = await client.post("/api/v1/crawl", json={})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_crawl_endpoint_valid_request(client: AsyncClient) -> None:
    """POST /api/v1/crawl with valid body must return 202."""
    response = await client.post(
        "/api/v1/crawl",
        json={"source": "reddit", "urls": ["https://reddit.com/r/python"]},
    )
    assert response.status_code == 202
    body = response.json()
    assert "run_id" in body
    assert body["status"] == "queued"


@pytest.mark.asyncio
async def test_pipeline_status_not_found(client: AsyncClient) -> None:
    """GET /api/v1/pipeline/status/<fake-id> must return 404."""
    response = await client.get("/api/v1/pipeline/status/fake-nonexistent-id")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_pipeline_run_endpoint(client: AsyncClient) -> None:
    """POST /api/v1/pipeline/run must return 200 with a run_id."""
    response = await client.post(
        "/api/v1/pipeline/run",
        json={"pipeline_id": "test-pipeline"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "run_id" in body


@pytest.mark.asyncio
async def test_pipeline_runs_list(client: AsyncClient) -> None:
    """GET /api/v1/pipeline/runs must return 200 with a list."""
    response = await client.get("/api/v1/pipeline/runs")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_datasets_endpoint_returns_list(client: AsyncClient) -> None:
    """GET /api/v1/datasets must return 200 with a DatasetListResponse."""
    response = await client.get("/api/v1/datasets")
    assert response.status_code == 200
    body = response.json()
    assert "datasets" in body
    assert "total" in body
    assert isinstance(body["datasets"], list)


@pytest.mark.asyncio
async def test_logs_endpoint_returns_logs(client: AsyncClient) -> None:
    """GET /api/v1/logs must return 200 with a LogsResponse."""
    response = await client.get("/api/v1/logs")
    assert response.status_code == 200
    body = response.json()
    assert "entries" in body
    assert "total" in body


@pytest.mark.asyncio
async def test_logs_endpoint_with_filters(client: AsyncClient) -> None:
    """GET /api/v1/logs with query params must return 200."""
    response = await client.get("/api/v1/logs?limit=10&level=INFO")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_dbt_build_endpoint(client: AsyncClient) -> None:
    """POST /api/v1/dbt/build must return 200."""
    response = await client.post("/api/v1/dbt/build", json={})
    assert response.status_code == 200
    body = response.json()
    assert "success" in body
    assert "output" in body


@pytest.mark.asyncio
async def test_dbt_test_endpoint(client: AsyncClient) -> None:
    """POST /api/v1/dbt/test must return 200."""
    response = await client.post("/api/v1/dbt/test", json={})
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_dbt_docs_endpoint(client: AsyncClient) -> None:
    """POST /api/v1/dbt/docs must return 200 with message and docs_url."""
    response = await client.post("/api/v1/dbt/docs")
    assert response.status_code == 200
    body = response.json()
    assert "message" in body
    assert "docs_url" in body


@pytest.mark.asyncio
async def test_kaggle_download_bad_slug(client: AsyncClient) -> None:
    """POST /kaggle/download with a non-slug format returns 400."""
    response = await client.post(
        "/api/v1/kaggle/download",
        json={"dataset": "nodashslash"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_kaggle_download_valid(client: AsyncClient) -> None:
    """POST /kaggle/download with a valid slug returns 200."""
    response = await client.post(
        "/api/v1/kaggle/download",
        json={"dataset": "owner/dataset"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "success" in body


@pytest.mark.asyncio
async def test_dashboard_endpoint(client: AsyncClient) -> None:
    """GET /api/v1/dashboard must return 200 with summary data."""
    response = await client.get("/api/v1/dashboard")
    assert response.status_code == 200
    body = response.json()
    assert "total_runs" in body
    assert "total_datasets" in body
