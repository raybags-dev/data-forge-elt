"""Router for pipeline run/status/cancel endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.schemas.pipeline import (
    PipelineRunRequest,
    PipelineRunResponse,
    PipelineStatusResponse,
)
from app.dependencies import get_pipeline_service
from app.services.pipeline_service import PipelineService

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


@router.post(
    "/run",
    response_model=PipelineRunResponse,
    status_code=status.HTTP_200_OK,
    summary="Trigger a pipeline run",
    description="Execute a named pipeline and return the completed run record.",
)
async def run_pipeline(
    request: PipelineRunRequest,
    service: PipelineService = Depends(get_pipeline_service),
) -> PipelineRunResponse:
    """Start and await a pipeline run.

    Args:
        request: PipelineRunRequest with pipeline_id and optional sources.
        service: Injected PipelineService.

    Returns:
        PipelineRunResponse with final run state.
    """
    return await service.run_pipeline(
        pipeline_id=request.pipeline_id,
        name=request.name,
        sources=request.sources,
    )


@router.get(
    "/status/{run_id}",
    response_model=PipelineStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get pipeline run status",
)
async def get_pipeline_status(
    run_id: str,
    service: PipelineService = Depends(get_pipeline_service),
) -> PipelineStatusResponse:
    """Return the current status of a pipeline run.

    Args:
        run_id: The run identifier to look up.
        service: Injected PipelineService.

    Returns:
        PipelineStatusResponse.

    Raises:
        HTTPException 404: If no run with the given ID exists.
    """
    result = await service.get_status(run_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No pipeline run found with id '{run_id}'",
        )
    return result


@router.get(
    "/runs",
    response_model=list[PipelineRunResponse],
    status_code=status.HTTP_200_OK,
    summary="List all pipeline runs",
)
async def list_runs(
    service: PipelineService = Depends(get_pipeline_service),
) -> list[PipelineRunResponse]:
    """Return all stored pipeline runs.

    Args:
        service: Injected PipelineService.

    Returns:
        List of PipelineRunResponse objects.
    """
    return await service.list_runs()


@router.post(
    "/cancel/{run_id}",
    status_code=status.HTTP_200_OK,
    summary="Cancel a pipeline run",
)
async def cancel_run(
    run_id: str,
    service: PipelineService = Depends(get_pipeline_service),
) -> dict:
    """Cancel a running pipeline.

    Args:
        run_id: The run to cancel.
        service: Injected PipelineService.

    Returns:
        Dict with 'cancelled' bool key.
    """
    cancelled = await service.cancel_run(run_id)
    return {"cancelled": cancelled}
