from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
from pydantic import BaseModel, Field

class DeploymentProviderType(str, Enum):
    VERCEL = "vercel"
    RENDER = "render"
    RAILWAY = "railway"
    FLY_IO = "fly_io"
    AWS = "aws"
    DIGITALOCEAN = "digitalocean"
    NETLIFY = "netlify"
    CUSTOM = "custom"

class DeploymentEnvironment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"

class DeploymentConfig(BaseModel):
    """Configuration for a deployment operation."""
    provider: DeploymentProviderType
    environment: DeploymentEnvironment = DeploymentEnvironment.PRODUCTION
    region: str = "us-east-1"
    
    # Feature Flags
    auto_deploy_on_git_push: bool = True
    health_check_enabled: bool = True
    monitoring_enabled: bool = True
    
    # Constraints
    cost_limit_monthly: Optional[float] = None
    
    # Provider-specific settings (passed through)
    extra_settings: Dict[str, Any] = Field(default_factory=dict)

class DeploymentResult(BaseModel):
    """Result of a deployment attempt."""
    success: bool
    deployment_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    provider: DeploymentProviderType
    environment: DeploymentEnvironment
    
    # URLs
    frontend_url: Optional[str] = None
    backend_url: Optional[str] = None
    database_url: Optional[str] = None # Often masked or internal
    
    # Metrics
    duration_seconds: float = 0.0
    
    # Logs/Feedback
    logs: List[str] = Field(default_factory=list)
    error_message: Optional[str] = None
    
    # Recovery
    rollback_id: Optional[str] = None

class VerificationCheck(BaseModel):
    """Result of a single health check."""
    name: str
    passed: bool
    details: str = ""
    latency_ms: float = 0.0

class VerificationReport(BaseModel):
    """Comprehensive health check report."""
    all_pass: bool
    checks: List[VerificationCheck] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class CostEstimate(BaseModel):
    """Monthly cost estimation."""
    provider: DeploymentProviderType
    total_monthly: float
    breakdown: Dict[str, float]
    currency: str = "USD"
    is_warning: bool = False # If exceeds limits
