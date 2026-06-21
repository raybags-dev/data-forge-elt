"""Router for dbt build/test/docs endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.api.schemas.dbt import DbtBuildRequest, DbtBuildResponse
from app.dependencies import get_dbt_service
from app.services.dbt_service import DbtService

router = APIRouter(prefix="/dbt", tags=["dbt"])


@router.post(
    "/build",
    response_model=DbtBuildResponse,
    status_code=status.HTTP_200_OK,
    summary="Run dbt build",
    description="Execute dbt build with an optional model selector.",
)
async def dbt_build(
    request: DbtBuildRequest,
    service: DbtService = Depends(get_dbt_service),
) -> DbtBuildResponse:
    """Run dbt build.

    Args:
        request: DbtBuildRequest with optional select and full_refresh.
        service: Injected DbtService.

    Returns:
        DbtBuildResponse with process output and model count.
    """
    return await service.build(select=request.select, full_refresh=request.full_refresh)


@router.post(
    "/test",
    response_model=DbtBuildResponse,
    status_code=status.HTTP_200_OK,
    summary="Run dbt test",
    description="Execute dbt test with an optional model selector.",
)
async def dbt_test(
    request: DbtBuildRequest,
    service: DbtService = Depends(get_dbt_service),
) -> DbtBuildResponse:
    """Run dbt test.

    Args:
        request: DbtBuildRequest with optional select.
        service: Injected DbtService.

    Returns:
        DbtBuildResponse with process output.
    """
    return await service.test(select=request.select)


@router.post(
    "/docs",
    status_code=status.HTTP_200_OK,
    summary="Generate dbt documentation",
    description="Run dbt docs generate and return the docs URL.",
)
async def dbt_docs(
    service: DbtService = Depends(get_dbt_service),
) -> dict:
    """Generate dbt documentation artefacts.

    Args:
        service: Injected DbtService.

    Returns:
        Dict with 'message' and 'docs_url' keys.
    """
    result = await service.docs_generate()
    docs_url = "http://localhost:8080" if result.success else ""
    return {
        "message": "docs generated successfully" if result.success else result.output,
        "docs_url": docs_url,
    }
