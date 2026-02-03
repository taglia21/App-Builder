import logging
from pathlib import Path
from typing import Dict, Optional, Type

from .base import BaseDeploymentProvider
from .models import DeploymentConfig, DeploymentResult
from .providers import ProviderDetector, RenderProvider, VercelProvider

logger = logging.getLogger(__name__)

class DeploymentEngine:
    """
    Orchestrates the deployment process across different providers.
    """

    def __init__(self):
        self._providers: Dict[str, Type[BaseDeploymentProvider]] = {}
        self._register_providers()

    def _register_providers(self):
        """Register supported providers."""
        self._providers["vercel"] = VercelProvider
        self._providers["render"] = RenderProvider

    def detect_available_providers(self) -> Dict[str, bool]:
        """Detect which providers are available in the current environment."""
        return ProviderDetector.detect_available_providers()

    def get_provider(self, provider_name: str) -> Optional[BaseDeploymentProvider]:
        """Instantiate a provider by name."""
        provider_cls = self._providers.get(provider_name.lower())
        if provider_cls:
            return provider_cls()
        return None

    async def deploy(
        self,
        codebase_path: str,
        config: DeploymentConfig,
        secrets: Dict[str, str] = None
    ) -> DeploymentResult:
        """
        Main entry point: Deploy codebase using the specified provider.
        """
        secrets = secrets or {}
        path = Path(codebase_path)

        if not path.exists():
            raise FileNotFoundError(f"Codebase path not found: {path}")

        provider = self.get_provider(config.provider)
        if not provider:
            return DeploymentResult(
                success=False,
                deployment_id="error",
                provider=config.provider,
                environment=config.environment,
                error_message=f"Provider '{config.provider}' not supported or not registered."
            )

        logger.info(f"🚀 Starting deployment to {config.provider} ({config.environment})...")

        # 1. Prerequisite Check
        prereqs = await provider.check_prerequisites()
        if not all(prereqs.values()):
            missing = [k for k, v in prereqs.items() if not v]
            return DeploymentResult(
                success=False,
                deployment_id="prereq_fail",
                provider=config.provider,
                environment=config.environment,
                error_message=f"Prerequisites missing: {', '.join(missing)}"
            )

        # 2. Deploy
        try:
            result = await provider.deploy(path, config, secrets)

            # 3. Post-Deployment Verification (if enabled)
            if result.success and config.health_check_enabled:
                logger.info("🔍 Running post-deployment health checks...")
                report = await provider.verify_deployment(result.deployment_id)
                if not report.all_pass:
                    logger.warning("⚠️ Deployment succeeded but health checks failed.")
                    result.error_message = f"Health check failures: {len([c for c in report.checks if not c.passed])}"
                    # Note: We don't mark result.success = False here, as the deploy technically worked.

            return result

        except Exception as e:
            logger.error(f"Deployment failed: {e}", exc_info=True)
            return DeploymentResult(
                success=False,
                deployment_id="exception",
                provider=config.provider,
                environment=config.environment,
                error_message=str(e)
            )
