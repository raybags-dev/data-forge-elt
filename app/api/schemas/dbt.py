"""Request/response schemas for the dbt endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field


class DbtBuildRequest(BaseModel):
    """Request body for dbt build/test commands.

    Attributes:
        select: Optional dbt model selector string.
        full_refresh: Run with --full-refresh to rebuild incremental models.
    """

    select: str | None = Field(default=None, description="dbt model selector (e.g. 'tag:daily')")
    full_refresh: bool = Field(
        default=False,
        description="Pass --full-refresh to dbt (rebuilds incremental models)",
    )


class DbtBuildResponse(BaseModel):
    """Response for dbt build/test operations.

    Attributes:
        success: Whether the dbt command exited with code 0.
        output: Combined stdout + stderr from the dbt process.
        duration_seconds: Wall-clock time for the command.
        models_run: Count of models processed (parsed from output).
    """

    success: bool
    output: str
    duration_seconds: float
    models_run: int = 0
