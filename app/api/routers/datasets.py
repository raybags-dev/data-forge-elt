"""Router for dataset discovery and preview endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.schemas.datasets import DatasetListResponse
from app.dependencies import get_dataset_service
from app.services.dataset_service import DatasetService

router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.get(
    "",
    response_model=DatasetListResponse,
    status_code=status.HTTP_200_OK,
    summary="List available datasets",
    description="Scan all lake layers for Parquet files and return metadata.",
)
async def list_datasets(
    service: DatasetService = Depends(get_dataset_service),
) -> DatasetListResponse:
    """Return all Parquet datasets found in the data lake.

    Args:
        service: Injected DatasetService.

    Returns:
        DatasetListResponse with metadata for each discovered file.
    """
    return service.list_datasets()


@router.get(
    "/{source}/{name}/preview",
    status_code=status.HTTP_200_OK,
    summary="Preview dataset rows",
    description="Read the first 100 rows of a named dataset.",
)
async def preview_dataset(
    source: str,
    name: str,
    service: DatasetService = Depends(get_dataset_service),
) -> list[dict]:
    """Return the first 100 rows of the specified dataset.

    Args:
        source: Source identifier (e.g. "kaggle", "reddit").
        name: Dataset filename stem.
        service: Injected DatasetService.

    Returns:
        List of row dicts.

    Raises:
        HTTPException 404: If no matching file is found.
    """
    rows = service.get_preview(source=source, name=name)
    if rows is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset '{source}/{name}' not found",
        )
    return rows
