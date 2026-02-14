"""
Example Plugin

Demonstrates how to write a Valeric pipeline plugin.
Logs lifecycle events — intended as living documentation.
"""

import logging
from typing import Any, Optional

from .base import PluginBase
from .registry import register_plugin

logger = logging.getLogger(__name__)


@register_plugin
class ExamplePlugin(PluginBase):
    """Logs every pipeline lifecycle event — useful for debugging."""

    def on_pipeline_start(self, build_id: str, config: dict[str, Any]) -> None:
        logger.info("[ExamplePlugin] pipeline started: build=%s", build_id)

    def on_stage_complete(self, build_id: str, stage: str, duration_ms: float) -> None:
        logger.info("[ExamplePlugin] stage complete: build=%s stage=%s duration=%.0fms", build_id, stage, duration_ms)

    def on_pipeline_complete(
        self,
        build_id: str,
        output_path: Optional[str],
        total_duration_ms: float,
    ) -> None:
        logger.info("[ExamplePlugin] pipeline complete: build=%s output=%s duration=%.0fms", build_id, output_path, total_duration_ms)

    def on_error(self, build_id: str, error: Exception) -> None:
        logger.error("[ExamplePlugin] pipeline error: build=%s error=%s", build_id, error)
