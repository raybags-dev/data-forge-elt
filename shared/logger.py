"""Production Loguru logging setup for DataForge ELT.

Usage:
    from shared.logger import get_logger, configure_logging, pipeline_context

    configure_logging(settings)
    logger = get_logger(__name__)

    with pipeline_context(pipeline_id="run-001", source="kaggle"):
        logger.info("Pipeline started")
"""

from __future__ import annotations

import sys
from collections.abc import Generator
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from typing import TYPE_CHECKING, Any

from loguru import logger

if TYPE_CHECKING:
    from loguru import Logger

    from config.settings import Settings

# ── Context variables bound into every log record ─────────────────────────────
_pipeline_id_var: ContextVar[str] = ContextVar("pipeline_id", default="")
_source_var: ContextVar[str] = ContextVar("source", default="")
_extra_var: ContextVar[dict[str, Any] | None] = ContextVar("extra", default=None)


def _build_format() -> str:
    """Return the structured log format string."""
    return (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{extra[name]}</cyan> | "
        "<level>{message}</level>"
        " | pipeline_id={extra[pipeline_id]}"
    )


def _patched_record(record: dict[str, Any]) -> None:
    """Inject context-var values into every log record's extra dict."""
    record["extra"].setdefault("pipeline_id", _pipeline_id_var.get())
    record["extra"].setdefault("source", _source_var.get())
    record["extra"].setdefault("name", record["name"])
    extra = _extra_var.get()
    if extra:
        for key, value in extra.items():
            record["extra"].setdefault(key, value)


def _memory_sink(message: Any) -> None:
    """Push log records into the in-memory stream for SSE delivery."""
    from shared.log_stream import push

    record = message.record
    push({
        "time": record["time"].isoformat(),
        "level": record["level"].name,
        "message": record["message"],
        "name": record["extra"].get("name", record.get("name", "")),
        "pipeline_id": record["extra"].get("pipeline_id", ""),
    })


def configure_logging(settings: Settings) -> None:
    """Configure all Loguru sinks from *settings*.

    Removes any previously registered sinks, then adds:
    - stderr sink at the configured log level.
    - rotating file sink at ``settings.log_dir / pipeline.log``.

    Args:
        settings: The application settings instance.
    """
    logger.remove()

    log_dir = Path(settings.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    logger.configure(patcher=_patched_record)

    logger.add(
        sys.stderr,
        level=settings.log_level,
        format=_build_format(),
        colorize=True,
        enqueue=False,
    )

    logger.add(
        str(log_dir / "pipeline.log"),
        level=settings.log_level,
        rotation=settings.log_rotation,
        retention=settings.log_retention,
        serialize=True,
        enqueue=True,
    )

    logger.add(_memory_sink, level=settings.log_level, enqueue=False)


def get_logger(name: str) -> Logger:
    """Return a Loguru logger bound with *name*.

    Args:
        name: Typically ``__name__`` of the calling module.

    Returns:
        A contextualized Loguru logger instance.
    """
    return logger.bind(name=name)


@contextmanager
def pipeline_context(
    pipeline_id: str,
    source: str = "",
    **extra: Any,
) -> Generator[None]:
    """Context manager that binds pipeline metadata to all log records within its scope.

    Args:
        pipeline_id: Unique identifier for this pipeline run.
        source: Data source name (e.g. "kaggle", "scraper").
        **extra: Any additional key-value pairs to bind.
    """
    pid_token = _pipeline_id_var.set(pipeline_id)
    src_token = _source_var.set(source)
    extra_token = _extra_var.set(extra)
    try:
        yield
    finally:
        _pipeline_id_var.reset(pid_token)
        _source_var.reset(src_token)
        _extra_var.reset(extra_token)
