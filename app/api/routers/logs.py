"""Router for the structured logs endpoint."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends, Query, status

from app.api.schemas.logs import LogEntry, LogsResponse
from app.dependencies import get_settings
from config.settings import Settings

router = APIRouter(prefix="/logs", tags=["logs"])


@router.get(
    "",
    response_model=LogsResponse,
    status_code=status.HTTP_200_OK,
    summary="Query structured logs",
    description="Return structured log entries filtered by level and pipeline_id.",
)
async def get_logs(
    limit: int = Query(default=100, ge=1, le=10_000, description="Max entries to return"),
    level: str | None = Query(default=None, description="Filter by log level (INFO, ERROR, ...)"),
    pipeline_id: str | None = Query(default=None, description="Filter by pipeline run ID"),
    settings: Settings = Depends(get_settings),
) -> LogsResponse:
    """Read the pipeline log file and return matching entries.

    Args:
        limit: Maximum number of log entries to return.
        level: Optional severity filter.
        pipeline_id: Optional pipeline ID filter.
        settings: Injected application settings.

    Returns:
        LogsResponse with filtered log entries.
    """
    log_file = Path(settings.log_dir) / "pipeline.log"
    entries = _read_log_file(log_file, limit=limit, level=level, pipeline_id=pipeline_id)
    return LogsResponse(entries=entries, total=len(entries))


def _read_log_file(
    log_file: Path,
    limit: int,
    level: str | None,
    pipeline_id: str | None,
) -> list[LogEntry]:
    """Parse the structured JSONL log file into LogEntry objects.

    Args:
        log_file: Path to the pipeline.log file.
        limit: Maximum entries to return.
        level: Optional level filter.
        pipeline_id: Optional pipeline_id filter.

    Returns:
        List of matching LogEntry objects.
    """
    if not log_file.exists():
        return []

    entries: list[LogEntry] = []
    try:
        lines = log_file.read_text(encoding="utf-8").splitlines()
    except Exception:
        return []

    for line in reversed(lines):
        if len(entries) >= limit:
            break
        entry = _parse_log_line(line)
        if entry is None:
            continue
        if level and entry.level.upper() != level.upper():
            continue
        if pipeline_id and entry.pipeline_id != pipeline_id:
            continue
        entries.append(entry)

    return list(reversed(entries))


def _parse_log_line(line: str) -> LogEntry | None:
    """Parse a single JSONL log line into a LogEntry.

    Args:
        line: Raw log line (JSONL format from Loguru serialize=True).

    Returns:
        LogEntry or None if the line cannot be parsed.
    """
    line = line.strip()
    if not line:
        return None
    try:
        data = json.loads(line)
        record = data.get("record", data)
        time_data = record.get("time", {})
        timestamp = time_data.get("repr", "") if isinstance(time_data, dict) else str(time_data)
        level_data = record.get("level", {})
        level_str = level_data.get("name", "INFO") if isinstance(level_data, dict) else str(level_data)
        message = record.get("message", str(data))
        extra = record.get("extra", {})
        pid = extra.get("pipeline_id") if isinstance(extra, dict) else None
        return LogEntry(
            timestamp=timestamp,
            level=level_str,
            message=message,
            pipeline_id=pid or None,
        )
    except (json.JSONDecodeError, KeyError, TypeError):
        return None
