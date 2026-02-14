"""
Plugin Registry

Central registry for discovering and calling plugin hooks.
"""

from __future__ import annotations

import logging
from typing import Any, Type

from .base import PluginBase

logger = logging.getLogger(__name__)


class PluginRegistry:
    """Stores registered plugins and fans-out hook calls with error isolation."""

    def __init__(self) -> None:
        self._plugins: list[PluginBase] = []

    def register(self, plugin: PluginBase) -> None:
        """Add a plugin instance to the registry."""
        self._plugins.append(plugin)
        logger.info("Plugin registered: %s", plugin.name)

    def call_hook(self, hook_name: str, **kwargs: Any) -> None:
        """Invoke *hook_name* on every registered plugin, catching errors."""
        for plugin in self._plugins:
            fn = getattr(plugin, hook_name, None)
            if fn is None:
                continue
            try:
                fn(**kwargs)
            except Exception:
                logger.warning(
                    "Plugin %s raised on hook %s",
                    plugin.name,
                    hook_name,
                    exc_info=True,
                )


# Module-level singleton
plugin_registry = PluginRegistry()


def register_plugin(cls: Type[PluginBase]) -> Type[PluginBase]:
    """Class decorator that instantiates and registers a plugin.

    Usage::

        @register_plugin
        class MyPlugin(PluginBase):
            ...
    """
    instance = cls()
    plugin_registry.register(instance)
    return cls
