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
    from pathlib import Path
    # Add src directory to path
    src_dir = Path(__file__).parent.parent
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))
    
    from config import (
        load_config,
        PipelineConfig,
        IntelligenceConfig,
        IdeaGenerationConfig,
        ScoringConfig,
        PromptEngineeringConfig,
        ExportConfig
    )
except (ImportError, AttributeError, Exception) as e:
    # Fallback if config.py doesn't have the classes
    import warnings
    warnings.warn(f"Could not import legacy config classes: {e}")
    
    def load_config(config_path=None):
        """Fallback load_config function."""
        return {}
    
    # Provide minimal classes for backward compatibility
    class PipelineConfig:
        """Fallback PipelineConfig."""
        def get_data_sources(self):
            return []
        
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


# Additional compatibility classes for tests
class DatabaseConfig:
    """Database configuration class for backward compatibility."""
    def __init__(self, url: str = None, **kwargs):
        self.url = url or settings.DATABASE_URL


class LLMConfig:
    """LLM configuration class for backward compatibility."""
    def __init__(self, **kwargs):
        self.openai_api_key = settings.OPENAI_API_KEY
        self.anthropic_api_key = settings.ANTHROPIC_API_KEY
        self.google_api_key = settings.GOOGLE_API_KEY

__all__ = [
    "Settings", "settings", "get_settings", "load_config",
    "PipelineConfig", "IntelligenceConfig", "IdeaGenerationConfig",
    "ScoringConfig", "PromptEngineeringConfig", "ExportConfig",
    "DatabaseConfig", "LLMConfig"
]
