"""Configuration package for LaunchForge."""

from .settings import Settings, settings


def get_settings() -> Settings:
    """Get the settings instance (for backward compatibility).
    
    Returns:
        Settings: The global settings instance
    """
    return settings

# Backward compatibility - import old config classes from parent module
try:
    import sys
    sys.path.insert(0, str(__file__.rsplit('/', 2)[0]))  # Add src to path
    
    from config import (
        load_config,
        PipelineConfig,
        IntelligenceConfig,
        IdeaGenerationConfig,
        ScoringConfig,
        PromptEngineeringConfig,
        ExportConfig
    )
except (ImportError, AttributeError, Exception):
    # Fallback if config.py doesn't have the classes
    def load_config(config_path=None):
        """Fallback load_config function."""
        return {}
    
    # Provide dummy classes for backward compatibility
    class PipelineConfig:
        pass
    class IntelligenceConfig:
        pass
    class IdeaGenerationConfig:
        pass
    class ScoringConfig:
        pass
    class PromptEngineeringConfig:
        pass
    class ExportConfig:
        pass

__all__ = [
    "Settings", "settings", "get_settings", "load_config",
    "PipelineConfig", "IntelligenceConfig", "IdeaGenerationConfig",
    "ScoringConfig", "PromptEngineeringConfig", "ExportConfig"
]
