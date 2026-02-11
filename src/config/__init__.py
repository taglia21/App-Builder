"""Configuration package for Valeric."""

import importlib.util
from pathlib import Path

from .settings import Settings, settings


def get_settings() -> Settings:
    """Get the settings instance (for backward compatibility).
    
    Returns:
        Settings: The global settings instance
    """
    return settings

# Load legacy config classes from src/config.py (sibling module)
# We use importlib to avoid circular import since this package shadows the module name.
_config_module_path = Path(__file__).parent.parent / "config.py"
try:
    _spec = importlib.util.spec_from_file_location("_legacy_config", _config_module_path)
    _mod = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)

    PipelineConfig = _mod.PipelineConfig
    IntelligenceConfig = _mod.IntelligenceConfig
    IdeaGenerationConfig = _mod.IdeaGenerationConfig
    ScoringConfig = _mod.ScoringConfig
    PromptEngineeringConfig = _mod.PromptEngineeringConfig

    _original_load_config = _mod.load_config

    def load_config(config_path: str = "config.yml") -> "PipelineConfig":
        """Load pipeline config from YAML, falling back to env-only config."""
        try:
            return _original_load_config(config_path)
        except FileNotFoundError:
            # No config.yml — use environment-variable-only defaults
            return PipelineConfig()

except Exception as e:
    import warnings
    warnings.warn(f"Could not import legacy config classes: {e}")

    def load_config(config_path=None):
        """Fallback load_config function."""
        return {}

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

# ExportConfig stub — not present in src/config.py, needed for backward compat
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
