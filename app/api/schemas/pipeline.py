"""Request/response schemas for the pipeline endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PipelineRunRequest(BaseModel):
    """Request body for POST /pipeline/run.

    Attributes:
        pipeline_id: Identifier of the registered pipeline to execute.
        name: Optional human-readable name for this run.
        sources: Data source identifiers (overrides registry defaults if set).
    """

    pipeline_id: str = Field(..., description="Registered pipeline identifier")
    name: str = Field(default="", description="Human-readable name for this run")
    sources: list[str] = Field(
        default_factory=list,
        description="Override data sources for this run",
    )


class PipelineRunResponse(BaseModel):
    """Response for a pipeline run creation or status query.

    Attributes:
        run_id: Unique identifier for this run.
        pipeline_id: The pipeline definition that was executed.
        status: Current lifecycle status.
        started_at: ISO-8601 start timestamp.
        ended_at: ISO-8601 end timestamp (None if still running).
        duration_seconds: Elapsed time in seconds.
        errors: List of error messages encountered.
        output_paths: Filesystem paths of produced artefacts.
    """

    run_id: str
    pipeline_id: str
    status: str
    started_at: str | None = None
    ended_at: str | None = None
    duration_seconds: float | None = None
    errors: list[str] = Field(default_factory=list)
    output_paths: list[str] = Field(default_factory=list)


class PipelineStatusResponse(BaseModel):
    """Response for GET /pipeline/status/{run_id}.

    Attributes:
        run_id: Unique run identifier.
        status: Current lifecycle status.
        duration_seconds: Elapsed time, or None if not finished.
        errors: Errors encountered during the run.
    """

    run_id: str
    status: str
    duration_seconds: float | None = None
    errors: list[str] = Field(default_factory=list)
