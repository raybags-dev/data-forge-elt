"""DbtService — executes dbt commands via subprocess."""

from __future__ import annotations

import re
import subprocess
import time
from typing import TYPE_CHECKING

from shared.logger import get_logger

from app.api.schemas.dbt import DbtBuildResponse

if TYPE_CHECKING:
    from config.settings import Settings


class DbtService:
    """Wraps dbt CLI operations for the API layer.

    Each public method builds the appropriate dbt command, executes it
    as a subprocess, and returns a structured DbtBuildResponse.

    Args:
        settings: Application settings with dbt project/profiles paths.
    """

    def __init__(self, settings: "Settings") -> None:
        self._settings = settings
        self._log = get_logger(__name__)

    async def build(
        self, select: str | None = None, full_refresh: bool = False
    ) -> DbtBuildResponse:
        """Run `dbt build` with an optional model selector.

        Args:
            select: dbt --select expression.
            full_refresh: Add --full-refresh flag.

        Returns:
            DbtBuildResponse with outcome metadata.
        """
        cmd = self._base_command("build")
        if select:
            cmd.extend(["--select", select])
        if full_refresh:
            cmd.append("--full-refresh")
        return await self.run_command(cmd)

    async def test(self, select: str | None = None) -> DbtBuildResponse:
        """Run `dbt test` with an optional model selector.

        Args:
            select: dbt --select expression.

        Returns:
            DbtBuildResponse with outcome metadata.
        """
        cmd = self._base_command("test")
        if select:
            cmd.extend(["--select", select])
        return await self.run_command(cmd)

    async def docs_generate(self) -> DbtBuildResponse:
        """Run `dbt docs generate`.

        Returns:
            DbtBuildResponse with outcome metadata.
        """
        cmd = self._base_command("docs", "generate")
        return await self.run_command(cmd)

    async def run_command(self, command: list[str]) -> DbtBuildResponse:
        """Execute an arbitrary dbt sub-command and return structured output.

        Args:
            command: Full command list (e.g. ["uv", "run", "dbt", "build", ...]).

        Returns:
            DbtBuildResponse parsed from the process output.
        """
        self._log.info(f"DbtService: running {' '.join(command)}")
        start = time.monotonic()

        try:
            proc = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=600,
            )
            duration = time.monotonic() - start
            combined = proc.stdout + proc.stderr
            return DbtBuildResponse(
                success=proc.returncode == 0,
                output=combined,
                duration_seconds=duration,
                models_run=self._parse_model_count(combined),
            )
        except Exception as exc:
            duration = time.monotonic() - start
            self._log.error(f"DbtService: command failed: {exc}")
            return DbtBuildResponse(
                success=False,
                output=str(exc),
                duration_seconds=duration,
                models_run=0,
            )

    def _base_command(self, *subcmds: str) -> list[str]:
        """Build the base dbt command with project/profiles paths.

        Args:
            *subcmds: dbt subcommand parts (e.g. "build" or "docs", "generate").

        Returns:
            Command list ready for subprocess.run.
        """
        return [
            "uv", "run", "dbt",
            *subcmds,
            "--project-dir", str(self._settings.dbt_project_dir),
            "--profiles-dir", str(self._settings.dbt_profiles_dir),
        ]

    @staticmethod
    def _parse_model_count(output: str) -> int:
        """Parse the number of models run from dbt output text.

        Handles patterns like "Completed successfully" "3 of 3 OK" etc.

        Args:
            output: Combined stdout+stderr from the dbt process.

        Returns:
            Number of models processed, or 0 if not parseable.
        """
        patterns = [
            r"(\d+)\s+of\s+\d+\s+(?:OK|ERROR|PASS|FAIL|WARN)",
            r"Done\. PASS=(\d+)",
            r"(\d+)\s+model",
        ]
        for pattern in patterns:
            matches = re.findall(pattern, output, re.IGNORECASE)
            if matches:
                try:
                    return max(int(m) for m in matches)
                except ValueError:
                    continue
        return 0
