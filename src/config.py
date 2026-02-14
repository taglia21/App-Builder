"""
Configuration management for the Startup Generator pipeline.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DataSourceConfig(BaseSettings):
    """Configuration for a data source."""

    type: str
    enabled: bool = True
    api_key: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    bearer_token: Optional[str] = None
    token: Optional[str] = None


class IntelligenceConfig(BaseSettings):
    """Configuration for intelligence gathering."""

    model_config = SettingsConfigDict(extra="allow")

    lookback_period: int = 30
    min_pain_points: int = 100
    data_sources: List[Dict[str, Any]] = Field(default_factory=list)


class IdeaGenerationConfig(BaseSettings):
    """Configuration for idea generation."""

    min_ideas: int = 50
    filters: Dict[str, Any] = Field(default_factory=dict)


class ScoringConfig(BaseSettings):
    """Configuration for idea scoring."""

    weights: Dict[str, float] = Field(default_factory=dict)
    min_total_score: float = 70.0


class PromptEngineeringConfig(BaseSettings):
    """Configuration for prompt engineering."""

    template_path: str = "./templates/product_prompt.md"
    include_sections: List[str] = Field(default_factory=list)
    min_core_features: int = 8
    min_secondary_features: int = 6
    min_ai_modules: int = 3
    min_user_flows: int = 6
    min_screens: int = 15
    min_components: int = 25


class RefinementConfig(BaseSettings):
    """Configuration for prompt refinement."""

    max_iterations: int = 10
    checks: List[str] = Field(default_factory=list)
    llm_provider: str = "openai"
    model: str = "gpt-4-turbo-preview"


class CodeGenerationConfig(BaseSettings):
    """Configuration for code generation."""

    backend: Dict[str, str] = Field(default_factory=dict)
    frontend: Dict[str, str] = Field(default_factory=dict)
    infrastructure: Dict[str, str] = Field(default_factory=dict)
    output_directory: str = "./generated_projects"
    llm_provider: str = "openai"
    model: str = "gpt-4-turbo-preview"


class ExecutionConfig(BaseSettings):
    """Configuration for pipeline execution."""

    schedule: str = "0 6 * * 1"
    notifications: Dict[str, str] = Field(default_factory=dict)
    logging: Dict[str, str] = Field(default_factory=dict)


class LLMConfig(BaseSettings):
    """Configuration for LLM providers."""

    openai: Dict[str, Any] = Field(default_factory=dict)
    anthropic: Dict[str, Any] = Field(default_factory=dict)


class DatabaseConfig(BaseSettings):
    """Configuration for database."""

    url: str
    pool_size: int = 10
    max_overflow: int = 20


class RedisConfig(BaseSettings):
    """Configuration for Redis."""

    url: str
    db: int = 0


class PipelineConfig(BaseSettings):
    """Main configuration for the startup generator pipeline."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow",
    )

    # Environment variables
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    google_api_key: Optional[str] = None
    reddit_client_id: Optional[str] = None
    reddit_client_secret: Optional[str] = None
    twitter_bearer_token: Optional[str] = None
    newsapi_key: Optional[str] = None
    youtube_api_key: Optional[str] = None
    github_token: Optional[str] = None
    database_url: str = "sqlite:///./startup_generator.db"
    redis_url: str = "redis://localhost:6379/0"
    slack_webhook_url: Optional[str] = None
    notification_email: Optional[str] = None
    environment: str = "development"
    debug: bool = False

    # Analytics configuration
    plausible_domain: Optional[str] = None
    plausible_enabled: bool = False
    google_analytics_id: Optional[str] = None
    google_analytics_api_secret: Optional[str] = None

    # Email configuration
    resend_api_key: Optional[str] = None
    from_email: str = "noreply@valeric.dev"
    support_email: str = "support@valeric.dev"

    # Sub-configurations
    intelligence: Optional[IntelligenceConfig] = None
    idea_generation: Optional[IdeaGenerationConfig] = None
    scoring: Optional[ScoringConfig] = None
    prompt_engineering: Optional[PromptEngineeringConfig] = None
    refinement: Optional[RefinementConfig] = None
    code_generation: Optional[CodeGenerationConfig] = None
    execution: Optional[ExecutionConfig] = None
    llm: Optional[LLMConfig] = None
    database: Optional[DatabaseConfig] = None
    redis: Optional[RedisConfig] = None

    @classmethod
    def from_yaml(cls, yaml_path: str) -> "PipelineConfig":
        """Load configuration from YAML file."""
        config_path = Path(yaml_path)
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {yaml_path}")

        with open(config_path, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)

        # Create sub-configs
        instance = cls()

        if "intelligence" in config_data:
            instance.intelligence = IntelligenceConfig(**config_data["intelligence"])

        if "idea_generation" in config_data:
            instance.idea_generation = IdeaGenerationConfig(**config_data["idea_generation"])

        if "scoring" in config_data:
            instance.scoring = ScoringConfig(**config_data["scoring"])

        if "prompt_engineering" in config_data:
            instance.prompt_engineering = PromptEngineeringConfig(
                **config_data["prompt_engineering"]
            )

        if "refinement" in config_data:
            instance.refinement = RefinementConfig(**config_data["refinement"])

        if "code_generation" in config_data:
            instance.code_generation = CodeGenerationConfig(**config_data["code_generation"])

        if "execution" in config_data:
            instance.execution = ExecutionConfig(**config_data["execution"])

        if "llm" in config_data:
            instance.llm = LLMConfig(**config_data["llm"])

        if "database" in config_data:
            instance.database = DatabaseConfig(**config_data["database"])

        if "redis" in config_data:
            instance.redis = RedisConfig(**config_data["redis"])

        # Store raw data source configs
        instance._data_sources = config_data.get("intelligence", {}).get("data_sources", [])

        return instance

    def get_data_sources(self) -> List[Dict[str, Any]]:
        """Get data source configurations."""
        return getattr(self, "_data_sources", [])


def load_config(config_path: str = "config.yml") -> PipelineConfig:
    """Load pipeline configuration."""
    return PipelineConfig.from_yaml(config_path)


# Cached settings singleton
_settings: Optional[PipelineConfig] = None


def get_settings() -> PipelineConfig:
    """Get the application settings singleton.

    Returns a cached PipelineConfig instance. Uses environment variables
    for configuration with optional YAML file loading.
    """
    global _settings
    if _settings is None:
        _settings = PipelineConfig()
    return _settings


def reset_settings() -> None:
    """Reset the cached settings singleton. Useful for testing."""
    global _settings
    _settings = None
