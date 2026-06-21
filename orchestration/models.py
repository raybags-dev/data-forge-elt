"""Pydantic models for pipeline orchestration."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from shared.metrics import PipelineMetrics


class PipelineStatus(str, Enum):
    """Lifecycle states for a pipeline run."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class PipelineStepModel(BaseModel):
    """Declarative description of a single pipeline step.

    Attributes:
        name: Unique step name within the pipeline.
        description: Human-readable description of what this step does.
        order: Execution order index (lower numbers run first).
    """

    name: str
    description: str = ""
    order: int = 0


class PipelineConfig(BaseModel):
    """Static configuration that describes a pipeline.

    Attributes:
        pipeline_id: Unique identifier for this pipeline type.
        name: Human-readable pipeline name.
        description: Detailed description.
        steps: Ordered list of step descriptors.
        sources: Data source identifiers this pipeline ingests from.
    """

    pipeline_id: str
    name: str
    description: str = ""
    steps: list[PipelineStepModel] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)


class PipelineRun(BaseModel):
    """Mutable runtime record for a single pipeline execution.

    Attributes:
        run_id: Unique run identifier (UUID string).
        config: The static PipelineConfig used for this run.
        status: Current lifecycle status.
        started_at: UTC datetime when the run began.
        ended_at: UTC datetime when the run finished (None while running).
        metrics: PipelineMetrics snapshot captured at completion.
        errors: List of error messages encountered during the run.
        output_paths: Filesystem paths of data artefacts produced.
    """

    run_id: str
    config: PipelineConfig
    status: PipelineStatus = PipelineStatus.PENDING
    started_at: datetime | None = None
    ended_at: datetime | None = None
    metrics: PipelineMetrics | None = None
    errors: list[str] = Field(default_factory=list)
    output_paths: list[str] = Field(default_factory=list)

    model_config = {"arbitrary_types_allowed": True}

    @property
    def duration_seconds(self) -> float | None:
        """Elapsed run time in seconds, or None if not yet finished."""
        if self.started_at is None or self.ended_at is None:
            return None
        return (self.ended_at - self.started_at).total_seconds()
