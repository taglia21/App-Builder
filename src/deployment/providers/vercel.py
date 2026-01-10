
import json
import logging
import asyncio
from typing import Dict, Tuple
from pathlib import Path

from ..base import BaseDeploymentProvider
from ..models import DeploymentConfig, DeploymentResult, VerificationReport, VerificationCheck

logger = logging.getLogger(__name__)

class VercelProvider(BaseDeploymentProvider):
    """
    Deploys to Vercel. 
    Focuses on Next.js 14 frontend deployment.
    """
    
    async def check_prerequisites(self) -> Dict[str, bool]:
        # In a real app, we might check if `vercel` CLI is in path
        # or if PERMANENT_AUTH_TOKEN is valid.
        return {
            "cli_installed": True, # Assumption for now or use shutil.which('vercel')
            "auth_token_present": True
        }

    def validate_config(self, config: DeploymentConfig) -> Tuple[bool, str]:
        if config.provider != "vercel":
            return False, "Provider must be 'vercel'"
        return True, ""

    async def deploy(self, codebase_path: Path, config: DeploymentConfig, secrets: Dict[str, str]) -> DeploymentResult:
        logger.info("Initializing Vercel deployment...")
        
        # 1. Generate vercel.json
        self._generate_vercel_config(codebase_path, config)
        
        # 2. Sync Secrets (Mocked)
        await self._sync_secrets(secrets)
        
        # 3. Trigger Deployment (Mock command)
        # cmd = f"vercel deploy --prod --token {secrets.get('VERCEL_TOKEN')}"
        logger.info("Executing Vercel CLI...")
        await asyncio.sleep(2) # Simulate deployment time
        
        deployment_id = f"dpl_vercel_{int(asyncio.get_running_loop().time())}"
        
        return DeploymentResult(
            success=True,
            deployment_id=deployment_id,
            provider=config.provider,
            environment=config.environment,
            frontend_url=f"https://{codebase_path.name}.vercel.app",
            logs=["Building...", "Optimizing...", "Done."],
            duration_seconds=15.5
        )

    async def verify_deployment(self, deployment_id: str) -> VerificationReport:
        # Mock verification
        return VerificationReport(
            all_pass=True,
            checks=[
                VerificationCheck(name="Frontend Accessible", passed=True, latency_ms=120),
                VerificationCheck(name="SSL Valid", passed=True)
            ]
        )

    async def rollback(self, deployment_id: str, rollback_to_id: str) -> bool:
        logger.info(f"Rolling back Vercel deployment {deployment_id} to {rollback_to_id}")
        return True

    def _generate_vercel_config(self, codebase_path: Path, config: DeploymentConfig):
        vercel_config = {
            "buildCommand": "npm run build",
            "installCommand": "npm ci",
            "framework": "nextjs",
            "regions": [config.region]
        }
        
        # Write to file
        config_path = codebase_path / "vercel.json"
        with open(config_path, "w") as f:
            json.dump(vercel_config, f, indent=2)
        logger.info(f"Generated {config_path}")

    async def _sync_secrets(self, secrets: Dict[str, str]):
        logger.info(f"Syncing {len(secrets)} secrets to Vercel...")
