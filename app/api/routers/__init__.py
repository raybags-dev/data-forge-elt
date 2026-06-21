"""API router package for DataForge ELT."""

from app.api.routers.crawl import router as crawl_router
from app.api.routers.dashboard import router as dashboard_router
from app.api.routers.datasets import router as datasets_router
from app.api.routers.dbt import router as dbt_router
from app.api.routers.kaggle import router as kaggle_router
from app.api.routers.logs import router as logs_router
from app.api.routers.pipeline import router as pipeline_router

__all__ = [
    "crawl_router",
    "kaggle_router",
    "pipeline_router",
    "dbt_router",
    "datasets_router",
    "dashboard_router",
    "logs_router",
]
