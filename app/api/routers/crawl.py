"""Router for /crawl endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, status

from app.api.schemas.crawl import AnalyzeRequest, AnalyzeResponse, CrawlRequest, CrawlResponse
from app.dependencies import get_crawl_service
from app.services.crawl_service import CrawlService

router = APIRouter(prefix="/crawl", tags=["crawl"])


@router.post(
    "",
    response_model=CrawlResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger a web crawl",
)
async def crawl(
    request: CrawlRequest,
    service: CrawlService = Depends(get_crawl_service),
) -> CrawlResponse:
    return await service.run_crawl(request)


@router.post(
    "/analyze",
    response_model=AnalyzeResponse,
    summary="LLM-assisted DOM analysis",
    description="Fetch a URL, pass its HTML to Groq, return detected container + field selectors.",
)
async def analyze(
    request: AnalyzeRequest,
    service: CrawlService = Depends(get_crawl_service),
) -> AnalyzeResponse:
    return await service.analyze(request)


@router.get(
    "/sources",
    response_model=dict[str, Any],
    summary="List built-in source configs",
)
async def list_sources(
    service: CrawlService = Depends(get_crawl_service),
) -> dict[str, Any]:
    return service.get_sources()


@router.get(
    "/status",
    summary="Crawler health check",
)
async def crawler_status() -> dict[str, str]:
    return {"status": "ready"}
