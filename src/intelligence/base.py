"""
Intelligence-Gathering Engine for collecting market data from multiple sources.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List

from loguru import logger

from ..models import SourceType


class DataSource(ABC):
    """Abstract base class for data sources."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize data source with configuration."""
        self.config = config
        self.enabled = config.get("enabled", True)

    @abstractmethod
    async def gather(self) -> List[Dict[str, Any]]:
        """Gather data from the source."""
        pass

    @abstractmethod
    def get_source_type(self) -> SourceType:
        """Get the source type."""
        pass


class DataSourceRegistry:
    """Registry for managing data sources."""

    def __init__(self):
        """Initialize the registry."""
        self._sources: Dict[str, type] = {}

    def register(self, source_type: str, source_class: type) -> None:
        """Register a data source class."""
        self._sources[source_type] = source_class
        logger.info(f"Registered data source: {source_type}")

    def create(self, source_type: str, config: Dict[str, Any]) -> DataSource:
        """Create a data source instance."""
        if source_type not in self._sources:
            raise ValueError(f"Unknown data source type: {source_type}")

        return self._sources[source_type](config)

    def get_available_sources(self) -> List[str]:
        """Get list of available source types."""
        return list(self._sources.keys())


# Global registry
registry = DataSourceRegistry()


def register_source(source_type: str):
    """Decorator to register a data source."""

    def decorator(cls):
        registry.register(source_type, cls)
        return cls

    return decorator
