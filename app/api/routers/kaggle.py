"""Router for POST /kaggle/download endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.schemas.kaggle import KaggleDownloadRequest, KaggleDownloadResponse
from app.dependencies import get_kaggle_service
from app.services.kaggle_service import KaggleService

router = APIRouter(prefix="/kaggle", tags=["kaggle"])


@router.post(
    "/download",
    response_model=KaggleDownloadResponse,
    status_code=status.HTTP_200_OK,
    summary="Download a Kaggle dataset",
    description="Download a Kaggle dataset by 'owner/name' slug and convert to Parquet.",
)
async def download_dataset(
    request: KaggleDownloadRequest,
    service: KaggleService = Depends(get_kaggle_service),
) -> KaggleDownloadResponse:
    """Download the requested Kaggle dataset.

    Args:
        request: KaggleDownloadRequest with dataset slug and force flag.
        service: Injected KaggleService.

    Returns:
        KaggleDownloadResponse with paths and row count.

    Raises:
        HTTPException 400: If the dataset slug is malformed.
    """
    if "/" not in request.dataset:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dataset must be in 'owner/name' format",
        )
    return await service.download(dataset=request.dataset, force=request.force)
