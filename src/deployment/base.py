import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Tuple

from .models import CostEstimate, DeploymentConfig, DeploymentResult, VerificationReport

logger = logging.getLogger(__name__)

class BaseDeploymentProvider(ABC):
    """
    Abstract base class for all deployment providers.
    Enforces a consistent interface for the Deployment Engine.
    """

    @abstractmethod
    async def check_prerequisites(self) -> Dict[str, bool]:
        """
        Verify if the necessary CLI tools and API keys are available.
        Returns: Dict of check results, e.g., {"cli_installed": True, "api_key_set": True}
        """
        pass

    @abstractmethod
    def validate_config(self, config: DeploymentConfig) -> Tuple[bool, str]:
        """
        Syntactic validation of the configuration for this provider.
        Returns: (is_valid, error_message)
        """
        pass

    @abstractmethod
    async def deploy(
        self,
        codebase_path: Path,
        config: DeploymentConfig,
        secrets: Dict[str, str]
    ) -> DeploymentResult:
        """
        Execute the deployment process.

        Args:
            codebase_path: Root directory of the code to deploy.
            config: Deployment settings.
            secrets: Dictionary of sensitive env vars (API keys, DB URLs).

        Returns:
            DeploymentResult with success status and public URLs.
        """
        pass

    @abstractmethod
    async def verify_deployment(self, deployment_id: str) -> VerificationReport:
        """
        Run health checks on a completed deployment.
        """
        pass

    @abstractmethod
    async def rollback(self, deployment_id: str, rollback_to_id: str) -> bool:
        """
        Revert a deployment to a previous state.
        """
        pass

    async def estimate_cost(self, config: DeploymentConfig) -> CostEstimate:
        """
        Estimate the monthly cost for this deployment configuration.
        Override this if the provider has a pricing API or known model.
        """
        # Default implementation returns zero/unknown
        return CostEstimate(
            provider=config.provider,
            total_monthly=0.0,
            breakdown={"base": 0.0}
        )

    async def setup_custom_domain(self, deployment_id: str, domain: str) -> bool:
        """
        Configure a custom domain (and SSL) for the deployment.
        """
        logger.warning(f"Custom domain setup not implemented for {self.__class__.__name__}")
        return False
