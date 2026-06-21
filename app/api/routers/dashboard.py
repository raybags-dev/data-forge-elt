"""Router for the dashboard summary endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.dependencies import get_dataset_service, get_pipeline_service
from app.services.dataset_service import DatasetService
from app.services.pipeline_service import PipelineService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    summary="Dashboard summary",
    description="Return aggregate counts of runs, datasets, and recent activity.",
)
async def get_dashboard(
    pipeline_service: PipelineService = Depends(get_pipeline_service),
    dataset_service: DatasetService = Depends(get_dataset_service),
) -> dict:
    """Aggregate pipeline and dataset metadata for the dashboard.

    Args:
        pipeline_service: Injected PipelineService.
        dataset_service: Injected DatasetService.

    Returns:
        Dict with summary statistics.
    """
    runs = await pipeline_service.list_runs()
    datasets = dataset_service.list_datasets()

    status_counts: dict[str, int] = {}
    for run in runs:
        status_counts[run.status] = status_counts.get(run.status, 0) + 1

    recent_runs = sorted(
        runs, key=lambda r: r.started_at or "", reverse=True
    )[:5]

    return {
        "total_runs": len(runs),
        "total_datasets": datasets.total,
        "status_counts": status_counts,
        "recent_runs": [r.model_dump() for r in recent_runs],
    }
