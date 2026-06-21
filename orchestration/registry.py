"""PipelineRegistry — maps pipeline names to PipelineConfig objects."""

from __future__ import annotations

from shared.logger import get_logger

from orchestration.models import PipelineConfig

_log = get_logger(__name__)


class PipelineRegistry:
    """In-memory registry of named pipeline configurations.

    Provides register, lookup, and list operations. The registry is
    intentionally simple — no persistence, no versioning. A real system
    would back this with a database or YAML config files.
    """

    def __init__(self) -> None:
        self._configs: dict[str, PipelineConfig] = {}

    def register(self, config: PipelineConfig) -> None:
        """Add or overwrite a pipeline configuration.

        Args:
            config: The PipelineConfig to register.
        """
        self._configs[config.pipeline_id] = config
        _log.info(f"Registered pipeline '{config.pipeline_id}'")

    def get(self, pipeline_id: str) -> PipelineConfig | None:
        """Return the config for *pipeline_id*, or None if not found.

        Args:
            pipeline_id: Identifier to look up.
        """
        return self._configs.get(pipeline_id)

    def list_all(self) -> list[PipelineConfig]:
        """Return all registered pipeline configurations.

        Returns:
            List of PipelineConfig objects.
        """
        return list(self._configs.values())

    def remove(self, pipeline_id: str) -> bool:
        """Remove a pipeline config from the registry.

        Args:
            pipeline_id: Identifier of the config to remove.

        Returns:
            True if removed, False if not found.
        """
        if pipeline_id not in self._configs:
            return False
        del self._configs[pipeline_id]
        _log.info(f"Removed pipeline '{pipeline_id}'")
        return True
