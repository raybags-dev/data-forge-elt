"""PipelineService — bridges the API layer and PipelineOrchestrator."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.api.schemas.pipeline import PipelineRunResponse, PipelineStatusResponse
from orchestration.models import PipelineConfig, PipelineRun, PipelineStepModel
from shared.logger import get_logger

if TYPE_CHECKING:
    from orchestration.pipeline import PipelineOrchestrator


class PipelineService:
    """Translates API requests into orchestrator operations.

    Args:
        orchestrator: PipelineOrchestrator that executes the runs.
    """

    def __init__(self, orchestrator: PipelineOrchestrator) -> None:
        self._orchestrator = orchestrator
        self._log = get_logger(__name__)

    async def run_pipeline(
        self,
        pipeline_id: str,
        name: str = "",
        sources: list[str] | None = None,
    ) -> PipelineRunResponse:
        """Create and execute a pipeline run.

        Args:
            pipeline_id: Pipeline definition identifier.
            name: Optional human-readable name.
            sources: Data sources to use for this run.

        Returns:
            PipelineRunResponse with the completed run state.
        """
        config = self._build_config(pipeline_id, name, sources or [])
        self._log.info(f"PipelineService: starting run for pipeline_id={pipeline_id}")
        run = self._orchestrator.run(config)
        return self._to_run_response(run)

    async def get_status(self, run_id: str) -> PipelineStatusResponse | None:
        """Return the status of a specific run.

        Args:
            run_id: The run identifier to look up.

        Returns:
            PipelineStatusResponse, or None if the run is not found.
        """
        run = self._orchestrator.get_run(run_id)
        if run is None:
            return None
        return PipelineStatusResponse(
            run_id=run.run_id,
            status=run.status.value,
            duration_seconds=run.duration_seconds,
            errors=run.errors,
        )

    async def list_runs(self) -> list[PipelineRunResponse]:
        """Return all stored pipeline runs.

        Returns:
            List of PipelineRunResponse objects.
        """
        return [self._to_run_response(r) for r in self._orchestrator.list_runs()]

    async def cancel_run(self, run_id: str) -> bool:
        """Cancel a running pipeline.

        Args:
            run_id: The run to cancel.

        Returns:
            True if cancelled, False otherwise.
        """
        return self._orchestrator.cancel_run(run_id)

    def _build_config(
        self, pipeline_id: str, name: str, sources: list[str]
    ) -> PipelineConfig:
        """Construct a PipelineConfig from API request fields.

        Args:
            pipeline_id: Pipeline identifier.
            name: Human-readable name.
            sources: Source identifiers for this run.

        Returns:
            Populated PipelineConfig.
        """
        return PipelineConfig(
            pipeline_id=pipeline_id,
            name=name or pipeline_id,
            description="API-triggered pipeline run",
            steps=[
                PipelineStepModel(name="crawl", order=1),
                PipelineStepModel(name="datalake", order=2),
                PipelineStepModel(name="warehouse_load", order=3),
                PipelineStepModel(name="dbt_build", order=4),
                PipelineStepModel(name="notify", order=5),
            ],
            sources=sources,
        )

    @staticmethod
    def _to_run_response(run: PipelineRun) -> PipelineRunResponse:
        """Convert a PipelineRun domain object to an API response model.

        Args:
            run: The pipeline run to convert.

        Returns:
            PipelineRunResponse.
        """
        return PipelineRunResponse(
            run_id=run.run_id,
            pipeline_id=run.config.pipeline_id,
            status=run.status.value,
            started_at=run.started_at.isoformat() if run.started_at else None,
            ended_at=run.ended_at.isoformat() if run.ended_at else None,
            duration_seconds=run.duration_seconds,
            errors=run.errors,
            output_paths=run.output_paths,
        )
