"""Router for POST /crawl endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.schemas.crawl import CrawlRequest, CrawlResponse
from app.dependencies import get_crawl_service
from app.services.crawl_service import CrawlService

router = APIRouter(prefix="/crawl", tags=["crawl"])


@router.post(
    "",
    response_model=CrawlResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger a web crawl",
    description="Queue a crawl for the specified source and seed URLs.",
)
async def crawl(
    request: CrawlRequest,
    service: CrawlService = Depends(get_crawl_service),
) -> CrawlResponse:
    """Accept a crawl request and return a queued-job response.

    Args:
        request: CrawlRequest with source, urls, and optional output_name.
        service: Injected CrawlService instance.

    Returns:
        CrawlResponse with run_id and output_path.

    Raises:
        HTTPException 422: If request validation fails (handled by FastAPI).
    """
    if not request.urls:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="At least one URL is required",
        )
    return await service.run_crawl(
        source=request.source,
        urls=request.urls,
        output_name=request.output_name,
    )
