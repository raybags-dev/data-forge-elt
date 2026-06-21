"""FastAPI dependency injection functions for DataForge ELT.

All dependencies follow the same pattern: accept resolved sub-dependencies
via FastAPI's Depends() system and return fully-wired collaborator instances.
"""

from __future__ import annotations

import functools

from fastapi import Depends

from config.settings import Settings, get_settings
from shared.logger import get_logger


@functools.lru_cache(maxsize=1)
def _cached_settings() -> Settings:
    """Return the singleton Settings instance (cached across requests)."""
    return get_settings()


def get_settings_dep() -> Settings:
    """Provide the application Settings as a FastAPI dependency.

    Returns:
        Cached Settings singleton.
    """
    return _cached_settings()


# Alias used by routers that import get_settings directly from this module
get_settings_alias = get_settings_dep


def get_notifier(settings: Settings = Depends(get_settings_dep)):
    """Build and return a Notifier from application settings.

    Args:
        settings: Injected Settings instance.

    Returns:
        Notifier configured with all active channels.
    """
    from shared.notifier import NotifierFactory

    return NotifierFactory.build_notifier(settings)


def get_lake(settings: Settings = Depends(get_settings_dep)):
    """Build and return a DataLakeManager.

    Args:
        settings: Injected Settings instance.

    Returns:
        DataLakeManager rooted at settings.data_lake.
    """
    from datalake.manager import DataLakeManager

    log = get_logger("datalake.manager")
    return DataLakeManager(base_path=settings.data_lake, logger=log)


def get_warehouse(settings: Settings = Depends(get_settings_dep)):
    """Build and return a DuckDBWarehouse.

    Args:
        settings: Injected Settings instance.

    Returns:
        DuckDBWarehouse backed by the configured DuckDB file.
    """
    from warehouse.duckdb.connection import DuckDBConnection
    from warehouse.duckdb.warehouse import DuckDBWarehouse

    log = get_logger("warehouse.duckdb")
    conn = DuckDBConnection(db_path=settings.duckdb_path)
    return DuckDBWarehouse(connection=conn, logger=log)


def get_orchestrator(
    warehouse=Depends(get_warehouse),
    lake=Depends(get_lake),
    notifier=Depends(get_notifier),
    settings: Settings = Depends(get_settings_dep),
):
    """Build and return a PipelineOrchestrator.

    Args:
        warehouse: Injected DuckDBWarehouse.
        lake: Injected DataLakeManager.
        notifier: Injected Notifier.
        settings: Injected Settings.

    Returns:
        PipelineOrchestrator wired with all collaborators.
    """
    from orchestration.pipeline import PipelineOrchestrator

    log = get_logger("orchestration.pipeline")
    return PipelineOrchestrator(
        warehouse=warehouse,
        lake=lake,
        notifier=notifier,
        settings=settings,
        logger=log,
    )


def get_pipeline_service(
    orchestrator=Depends(get_orchestrator),
):
    """Return a PipelineService wrapping the orchestrator.

    Args:
        orchestrator: Injected PipelineOrchestrator.

    Returns:
        PipelineService instance.
    """
    from app.services.pipeline_service import PipelineService

    return PipelineService(orchestrator=orchestrator)


def get_crawl_service(
    settings: Settings = Depends(get_settings_dep),
    notifier=Depends(get_notifier),
    lake=Depends(get_lake),
):
    """Return a CrawlService for web-crawling operations.

    Args:
        settings: Injected Settings.
        notifier: Injected Notifier.
        lake: Injected DataLakeManager.

    Returns:
        CrawlService instance.
    """
    from app.services.crawl_service import CrawlService

    return CrawlService(settings=settings, notifier=notifier, lake=lake)


def get_kaggle_service(
    settings: Settings = Depends(get_settings_dep),
    notifier=Depends(get_notifier),
):
    """Return a KaggleService for dataset downloads.

    Args:
        settings: Injected Settings.
        notifier: Injected Notifier.

    Returns:
        KaggleService instance.
    """
    from app.services.kaggle_service import KaggleService

    return KaggleService(settings=settings, notifier=notifier)


def get_dbt_service(settings: Settings = Depends(get_settings_dep)):
    """Return a DbtService for dbt CLI operations.

    Args:
        settings: Injected Settings.

    Returns:
        DbtService instance.
    """
    from app.services.dbt_service import DbtService

    return DbtService(settings=settings)


def get_dataset_service(lake=Depends(get_lake)):
    """Return a DatasetService for lake dataset discovery.

    Args:
        lake: Injected DataLakeManager.

    Returns:
        DatasetService instance.
    """
    from app.services.dataset_service import DatasetService

    return DatasetService(lake=lake)
