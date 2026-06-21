"""Request/response schemas for the logs endpoint."""

from __future__ import annotations

from pydantic import BaseModel, Field


class LogEntry(BaseModel):
    """A single structured log record.

    Attributes:
        timestamp: ISO-8601 timestamp of the log event.
        level: Severity level string (e.g. INFO, ERROR).
        message: Log message text.
        pipeline_id: Associated pipeline run identifier, if any.
    """

    timestamp: str
    level: str
    message: str
    pipeline_id: str | None = None


class LogsResponse(BaseModel):
    """Response for GET /logs.

    Attributes:
        entries: List of log entries matching the query filters.
        total: Total number of matching entries returned.
    """

    entries: list[LogEntry] = Field(default_factory=list)
    total: int = 0
