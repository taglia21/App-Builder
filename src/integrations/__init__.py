"""Valeric Integrations Module - All Real Service Integrations"""

from .business_formation import BusinessFormationService
from .deployment_service import DeploymentService
from .github_integration import GitHubIntegration
from .live_preview import LivePreviewService
from .project_persistence import ProjectPersistenceService

# DomainService is now canonical in src.business.domain
# This re-export is kept for backward compatibility
try:
    from src.business.domain import DomainService
except ImportError:
    from .domain_service import DomainService

__all__ = [
    'GitHubIntegration',
    'DeploymentService',
    'BusinessFormationService',
    'DomainService',
    'LivePreviewService',
    'ProjectPersistenceService'
]
