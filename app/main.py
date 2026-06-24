"""FastAPI application factory for DataForge ELT.

Usage:
    uvicorn app.main:app --reload
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from shared.exceptions import DataForgeError
from shared.logger import configure_logging, get_logger

_log = get_logger(__name__)

_APP_VERSION = "1.0.0"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Handle application startup and shutdown events.

    Startup:
        - Configure logging sinks.
        - Ensure data lake directories exist.

    Shutdown:
        - Log graceful shutdown.
    """
    import asyncio as _asyncio

    from config.settings import get_settings
    from datalake.manager import DataLakeManager
    from shared.log_stream import set_loop as _set_log_loop

    settings = get_settings()
    configure_logging(settings)
    _set_log_loop(_asyncio.get_running_loop())
    _log.info(f"DataForge ELT API v{_APP_VERSION} starting up")

    lake_log = get_logger("datalake.manager")
    lake = DataLakeManager(base_path=settings.data_lake, logger=lake_log)
    lake.setup()

    yield

    _log.info("DataForge ELT API shutting down")


def create_app() -> FastAPI:
    """Build and return the configured FastAPI application.

    Mounts all API routers, registers middleware and exception handlers,
    and attaches the startup/shutdown lifespan.

    Returns:
        Fully configured FastAPI application instance.
    """
    app = FastAPI(
        title="DataForge ELT API",
        version=_APP_VERSION,
        description=(
            "DataForge ELT — production-quality pipeline orchestration with "
            "Playwright crawlers, Kaggle ingestion, DuckDB warehouse, and dbt "
            "transformations. Exposes REST endpoints for triggering and monitoring "
            "all pipeline stages."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    _add_cors(app)
    _add_exception_handlers(app)
    _mount_routers(app)
    _add_health_check(app)

    return app


def _add_cors(app: FastAPI) -> None:
    """Register CORS middleware (allow all origins for development).

    Args:
        app: FastAPI instance to configure.
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def _add_exception_handlers(app: FastAPI) -> None:
    """Register global exception handlers for DataForge errors.

    Args:
        app: FastAPI instance to configure.
    """

    @app.exception_handler(DataForgeError)
    async def dataforge_error_handler(
        request: Request, exc: DataForgeError
    ) -> JSONResponse:
        """Convert DataForgeError subclasses to structured HTTP responses."""
        from shared.exceptions import APIError

        status_code = exc.status_code if isinstance(exc, APIError) else 500
        _log.error(f"DataForgeError: {exc.message} context={exc.context}")
        return JSONResponse(
            status_code=status_code,
            content={"detail": exc.message, "context": exc.context},
        )


def _mount_routers(app: FastAPI) -> None:
    """Include all API routers under /api/v1 prefix.

    Args:
        app: FastAPI instance to configure.
    """
    from app.api.routers.crawl import router as crawl_router
    from app.api.routers.dashboard import router as dashboard_router
    from app.api.routers.datasets import router as datasets_router
    from app.api.routers.dbt import router as dbt_router
    from app.api.routers.kaggle import router as kaggle_router
    from app.api.routers.logs import router as logs_router
    from app.api.routers.pipeline import router as pipeline_router
    from app.api.routers.tokens import router as tokens_router

    prefix = "/api/v1"
    app.include_router(crawl_router, prefix=prefix)
    app.include_router(kaggle_router, prefix=prefix)
    app.include_router(pipeline_router, prefix=prefix)
    app.include_router(dbt_router, prefix=prefix)
    app.include_router(datasets_router, prefix=prefix)
    app.include_router(dashboard_router, prefix=prefix)
    app.include_router(logs_router, prefix=prefix)
    app.include_router(tokens_router, prefix=prefix)


def _add_health_check(app: FastAPI) -> None:
    """Register the /health endpoint.

    Args:
        app: FastAPI instance to configure.
    """

    @app.get("/health", tags=["meta"], summary="Health check")
    async def health() -> dict:
        """Return API health status.

        Returns:
            Dict with status and version.
        """
        return {"status": "ok", "version": _APP_VERSION}


# Module-level app instance for uvicorn
app = create_app()
