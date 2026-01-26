"""
NexusAI Database Module

PostgreSQL database integration with SQLAlchemy ORM.
Provides models, utilities, and connection management for production use.
"""

from src.database.models import (
    Base,
    User,
    Project,
    Generation,
    Deployment,
    SubscriptionTier,
    ProjectStatus,
    DeploymentStatus,
)
from src.database.db import (
    DatabaseManager,
    get_db,
    init_db,
    get_database_url,
)

__all__ = [
    # Base
    "Base",
    # Models
    "User",
    "Project",
    "Generation",
    "Deployment",
    # Enums
    "SubscriptionTier",
    "ProjectStatus",
    "DeploymentStatus",
    # Database utilities
    "DatabaseManager",
    "get_db",
    "init_db",
    "get_database_url",
]
