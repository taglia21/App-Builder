"""Data models for app generation."""
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class AppType(str, Enum):
    SAAS = "saas"
    MARKETPLACE = "marketplace"
    ECOMMERCE = "ecommerce"
    DASHBOARD = "dashboard"
    SOCIAL = "social"
    PORTFOLIO = "portfolio"
    API = "api"
    OTHER = "other"


class TechStack(str, Enum):
    PYTHON_FASTAPI = "python-fastapi"
    NEXTJS = "nextjs"
    DJANGO = "django"
    FLASK = "flask"
    EXPRESS = "express"


class Feature(str, Enum):
    AUTH = "auth"
    PAYMENTS = "payments"
    DATABASE = "database"
    API = "api"
    EMAIL = "email"
    REALTIME = "realtime"


@dataclass
class GenerationRequest:
    """Request to generate an app."""
    project_name: str
    description: str
    app_type: AppType
    tech_stack: TechStack
    features: List[Feature]
    user_id: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class GeneratedFile:
    """A single generated file."""
    path: str
    content: str
    language: str = "python"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "content": self.content,
            "language": self.language
        }


@dataclass
class GeneratedApp:
    """Complete generated application."""
    id: str
    project_name: str
    files: List[GeneratedFile]
    tech_stack: TechStack
    features: List[Feature]
    readme: str
    requirements: List[str]
    env_template: str
    docker_compose: Optional[str] = None
    dockerfile: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "project_name": self.project_name,
            "files": [f.to_dict() for f in self.files],
            "tech_stack": self.tech_stack.value,
            "features": [f.value for f in self.features],
            "readme": self.readme,
            "requirements": self.requirements,
            "env_template": self.env_template,
            "dockerfile": self.dockerfile,
            "docker_compose": self.docker_compose,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class GenerationProgress:
    """Progress update during generation."""
    step: str
    progress: int  # 0-100
    message: str
    files_generated: int = 0
    total_files: int = 0
