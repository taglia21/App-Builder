"""
Plugin Base Class

Abstract base class for Valeric pipeline plugins.  All hooks have default
no-op implementations so plugins can override only what they need.
"""

from __future__ import annotations

from typing import Any, Optional


class PluginBase:
    """Base class for pipeline plugins.

    Override any hook method to react to pipeline lifecycle events.
    All hooks are no-ops by default.
    """

    @property
    def name(self) -> str:
        """Human-readable plugin name (defaults to class name)."""
        return self.__class__.__name__

    # ---- lifecycle hooks (all no-ops) ------------------------------------

    def on_pipeline_start(self, build_id: str, config: dict[str, Any]) -> None:
        """Called when the pipeline starts."""

    def on_stage_complete(self, build_id: str, stage: str, duration_ms: float) -> None:
        """Called after each pipeline stage finishes."""

    def on_pipeline_complete(
        self,
        build_id: str,
        output_path: Optional[str],
        total_duration_ms: float,
    ) -> None:
        """Called when the full pipeline completes successfully."""

    def on_error(self, build_id: str, error: Exception) -> None:
        """Called when the pipeline fails."""
