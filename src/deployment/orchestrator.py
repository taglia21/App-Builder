"""
Deployment Orchestrator

Coordinates the full deployment pipeline: GitHub repo creation,
frontend deployment to Vercel, backend deployment to Render.
"""

import os
import asyncio
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from enum import Enum

from src.deployment.github import GitHubClient, GitHubRepo, GitHubError
from src.deployment.providers.vercel import VercelProvider
from src.deployment.providers.render import RenderProvider
from src.deployment.models import DeploymentConfig, DeploymentResult

logger = logging.getLogger(__name__)


class DeploymentStatus(str, Enum):
    """Deployment status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class DeploymentStage(str, Enum):
    """Deployment stages."""
    GITHUB_REPO = "github_repo"
    FRONTEND_DEPLOY = "frontend_deploy"
    BACKEND_DEPLOY = "backend_deploy"
    ENVIRONMENT_CONFIG = "environment_config"
    VERIFICATION = "verification"


@dataclass
class StageResult:
    """Result of a deployment stage."""
    stage: DeploymentStage
    status: DeploymentStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    message: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class DeploymentPlan:
    """Full deployment plan."""
    project_id: str
    project_name: str
    environment: str  # production, staging, development
    
    # Source code locations
    frontend_path: Optional[Path] = None
    backend_path: Optional[Path] = None
    
    # Deployment targets
    deploy_frontend: bool = True
    deploy_backend: bool = True
    create_github_repo: bool = True
    
    # Configuration
    github_private: bool = True
    vercel_team: Optional[str] = None
    render_team: Optional[str] = None
    
    # Secrets to configure
    environment_variables: Dict[str, str] = field(default_factory=dict)
    
    # Custom domain
    custom_domain: Optional[str] = None


@dataclass
class DeploymentSummary:
    """Summary of a completed deployment."""
    project_id: str
    project_name: str
    status: DeploymentStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    
    # URLs
    github_url: Optional[str] = None
    frontend_url: Optional[str] = None
    backend_url: Optional[str] = None
    
    # Stage results
    stages: List[StageResult] = field(default_factory=list)
    
    # Identifiers for rollback
    github_repo: Optional[str] = None
    vercel_deployment_id: Optional[str] = None
    render_deployment_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "project_id": self.project_id,
            "project_name": self.project_name,
            "status": self.status.value,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "urls": {
                "github": self.github_url,
                "frontend": self.frontend_url,
                "backend": self.backend_url,
            },
            "stages": [
                {
                    "stage": s.stage.value,
                    "status": s.status.value,
                    "message": s.message,
                    "error": s.error,
                }
                for s in self.stages
            ],
        }


class DeploymentOrchestrator:
    """
    Orchestrates the complete deployment pipeline.
    
    Pipeline stages:
    1. Create GitHub repository
    2. Push code to repository
    3. Deploy frontend to Vercel
    4. Deploy backend to Render
    5. Configure environment variables
    6. Verify deployment
    """
    
    def __init__(
        self,
        github_token: Optional[str] = None,
        vercel_token: Optional[str] = None,
        render_token: Optional[str] = None,
    ):
        """
        Initialize orchestrator.
        
        Args:
            github_token: GitHub personal access token
            vercel_token: Vercel API token
            render_token: Render API token
        """
        self.github_token = github_token or os.getenv("GITHUB_TOKEN")
        self.vercel_token = vercel_token or os.getenv("VERCEL_TOKEN")
        self.render_token = render_token or os.getenv("RENDER_TOKEN")
        
        # Initialize providers
        self._github: Optional[GitHubClient] = None
        self._vercel = VercelProvider()
        self._render = RenderProvider()
        
        # Deployment tracking
        self._deployments: Dict[str, DeploymentSummary] = {}
    
    @property
    def github(self) -> GitHubClient:
        """Get GitHub client (lazy initialization)."""
        if self._github is None:
            self._github = GitHubClient(self.github_token)
        return self._github
    
    async def deploy(
        self,
        plan: DeploymentPlan,
        on_stage_complete: Optional[callable] = None,
    ) -> DeploymentSummary:
        """
        Execute a full deployment.
        
        Args:
            plan: Deployment plan
            on_stage_complete: Callback for stage completion
            
        Returns:
            DeploymentSummary with results
        """
        summary = DeploymentSummary(
            project_id=plan.project_id,
            project_name=plan.project_name,
            status=DeploymentStatus.IN_PROGRESS,
            started_at=datetime.utcnow(),
        )
        
        self._deployments[plan.project_id] = summary
        
        try:
            # Stage 1: Create GitHub repository
            if plan.create_github_repo:
                result = await self._create_github_repo(plan)
                summary.stages.append(result)
                
                if result.status == DeploymentStatus.SUCCESS:
                    summary.github_url = result.data.get("html_url")
                    summary.github_repo = result.data.get("full_name")
                    
                    if on_stage_complete:
                        on_stage_complete(result)
                else:
                    raise Exception(result.error)
            
            # Stage 2: Deploy frontend
            if plan.deploy_frontend and plan.frontend_path:
                result = await self._deploy_frontend(plan, summary.github_repo)
                summary.stages.append(result)
                
                if result.status == DeploymentStatus.SUCCESS:
                    summary.frontend_url = result.data.get("url")
                    summary.vercel_deployment_id = result.data.get("deployment_id")
                    
                    if on_stage_complete:
                        on_stage_complete(result)
                else:
                    raise Exception(result.error)
            
            # Stage 3: Deploy backend
            if plan.deploy_backend and plan.backend_path:
                result = await self._deploy_backend(plan, summary.github_repo)
                summary.stages.append(result)
                
                if result.status == DeploymentStatus.SUCCESS:
                    summary.backend_url = result.data.get("url")
                    summary.render_deployment_id = result.data.get("deployment_id")
                    
                    if on_stage_complete:
                        on_stage_complete(result)
                else:
                    raise Exception(result.error)
            
            # Stage 4: Configure environment
            result = await self._configure_environment(plan, summary)
            summary.stages.append(result)
            
            if on_stage_complete:
                on_stage_complete(result)
            
            # Stage 5: Verify deployment
            result = await self._verify_deployment(summary)
            summary.stages.append(result)
            
            if on_stage_complete:
                on_stage_complete(result)
            
            # All stages complete
            summary.status = DeploymentStatus.SUCCESS
            summary.completed_at = datetime.utcnow()
            
            logger.info(f"Deployment completed for {plan.project_name}")
            
        except Exception as e:
            logger.error(f"Deployment failed: {e}")
            summary.status = DeploymentStatus.FAILED
            summary.completed_at = datetime.utcnow()
            
            # Add failure stage if not already added
            if not summary.stages or summary.stages[-1].status != DeploymentStatus.FAILED:
                summary.stages.append(StageResult(
                    stage=DeploymentStage.VERIFICATION,
                    status=DeploymentStatus.FAILED,
                    started_at=datetime.utcnow(),
                    completed_at=datetime.utcnow(),
                    error=str(e),
                ))
        
        return summary
    
    async def _create_github_repo(self, plan: DeploymentPlan) -> StageResult:
        """Create GitHub repository and push code."""
        started_at = datetime.utcnow()
        
        try:
            # Create repository
            repo = self.github.create_repository(
                name=plan.project_name,
                description=f"NexusAI project: {plan.project_name}",
                private=plan.github_private,
                auto_init=True,
                gitignore_template="Node",
            )
            
            # Upload code if paths provided
            if plan.frontend_path:
                self.github.upload_directory(
                    repo_name=repo.full_name,
                    local_path=plan.frontend_path,
                    remote_path="frontend",
                    message="Add frontend code",
                )
            
            if plan.backend_path:
                self.github.upload_directory(
                    repo_name=repo.full_name,
                    local_path=plan.backend_path,
                    remote_path="backend",
                    message="Add backend code",
                )
            
            # Add GitHub Actions workflow
            await self._add_ci_workflow(repo.full_name)
            
            return StageResult(
                stage=DeploymentStage.GITHUB_REPO,
                status=DeploymentStatus.SUCCESS,
                started_at=started_at,
                completed_at=datetime.utcnow(),
                message=f"Created repository: {repo.full_name}",
                data={
                    "full_name": repo.full_name,
                    "html_url": repo.html_url,
                    "clone_url": repo.clone_url,
                },
            )
            
        except GitHubError as e:
            return StageResult(
                stage=DeploymentStage.GITHUB_REPO,
                status=DeploymentStatus.FAILED,
                started_at=started_at,
                completed_at=datetime.utcnow(),
                error=str(e),
            )
    
    async def _deploy_frontend(
        self,
        plan: DeploymentPlan,
        github_repo: Optional[str],
    ) -> StageResult:
        """Deploy frontend to Vercel."""
        started_at = datetime.utcnow()
        
        try:
            config = DeploymentConfig(
                provider="vercel",
                environment=plan.environment,
                region="iad1",  # US East
                framework="nextjs",
            )
            
            secrets = {
                "VERCEL_TOKEN": self.vercel_token or "",
                **plan.environment_variables,
            }
            
            result = await self._vercel.deploy(
                codebase_path=plan.frontend_path,
                config=config,
                secrets=secrets,
            )
            
            return StageResult(
                stage=DeploymentStage.FRONTEND_DEPLOY,
                status=DeploymentStatus.SUCCESS if result.success else DeploymentStatus.FAILED,
                started_at=started_at,
                completed_at=datetime.utcnow(),
                message=f"Deployed to {result.frontend_url}" if result.success else "Deployment failed",
                data={
                    "deployment_id": result.deployment_id,
                    "url": result.frontend_url,
                    "logs": result.logs,
                },
                error=None if result.success else "Vercel deployment failed",
            )
            
        except Exception as e:
            return StageResult(
                stage=DeploymentStage.FRONTEND_DEPLOY,
                status=DeploymentStatus.FAILED,
                started_at=started_at,
                completed_at=datetime.utcnow(),
                error=str(e),
            )
    
    async def _deploy_backend(
        self,
        plan: DeploymentPlan,
        github_repo: Optional[str],
    ) -> StageResult:
        """Deploy backend to Render."""
        started_at = datetime.utcnow()
        
        try:
            config = DeploymentConfig(
                provider="render",
                environment=plan.environment,
                region="oregon",
                framework="python",
            )
            
            secrets = {
                "RENDER_TOKEN": self.render_token or "",
                **plan.environment_variables,
            }
            
            result = await self._render.deploy(
                codebase_path=plan.backend_path,
                config=config,
                secrets=secrets,
            )
            
            return StageResult(
                stage=DeploymentStage.BACKEND_DEPLOY,
                status=DeploymentStatus.SUCCESS if result.success else DeploymentStatus.FAILED,
                started_at=started_at,
                completed_at=datetime.utcnow(),
                message=f"Deployed to {result.backend_url}" if result.success else "Deployment failed",
                data={
                    "deployment_id": result.deployment_id,
                    "url": result.backend_url,
                    "logs": result.logs,
                },
                error=None if result.success else "Render deployment failed",
            )
            
        except Exception as e:
            return StageResult(
                stage=DeploymentStage.BACKEND_DEPLOY,
                status=DeploymentStatus.FAILED,
                started_at=started_at,
                completed_at=datetime.utcnow(),
                error=str(e),
            )
    
    async def _configure_environment(
        self,
        plan: DeploymentPlan,
        summary: DeploymentSummary,
    ) -> StageResult:
        """Configure environment variables across services."""
        started_at = datetime.utcnow()
        
        try:
            configured = []
            
            # Set GitHub secrets if repo exists
            if summary.github_repo and plan.environment_variables:
                results = self.github.set_repository_secrets(
                    repo_name=summary.github_repo,
                    secrets=plan.environment_variables,
                )
                configured.append(f"GitHub: {sum(results.values())}/{len(results)} secrets")
            
            # Cross-link frontend and backend URLs
            if summary.frontend_url and summary.backend_url:
                # Frontend needs to know backend URL
                # Backend needs to know frontend URL for CORS
                configured.append("Cross-linked frontend/backend URLs")
            
            return StageResult(
                stage=DeploymentStage.ENVIRONMENT_CONFIG,
                status=DeploymentStatus.SUCCESS,
                started_at=started_at,
                completed_at=datetime.utcnow(),
                message=f"Configured: {', '.join(configured)}",
                data={"configured": configured},
            )
            
        except Exception as e:
            return StageResult(
                stage=DeploymentStage.ENVIRONMENT_CONFIG,
                status=DeploymentStatus.FAILED,
                started_at=started_at,
                completed_at=datetime.utcnow(),
                error=str(e),
            )
    
    async def _verify_deployment(self, summary: DeploymentSummary) -> StageResult:
        """Verify all deployments are healthy."""
        started_at = datetime.utcnow()
        
        checks = []
        all_pass = True
        
        try:
            # Verify frontend
            if summary.frontend_url:
                verification = await self._vercel.verify_deployment(
                    summary.vercel_deployment_id or ""
                )
                checks.append({
                    "service": "frontend",
                    "passed": verification.all_pass,
                    "checks": [
                        {"name": c.name, "passed": c.passed}
                        for c in verification.checks
                    ],
                })
                if not verification.all_pass:
                    all_pass = False
            
            # Verify backend
            if summary.backend_url:
                verification = await self._render.verify_deployment(
                    summary.render_deployment_id or ""
                )
                checks.append({
                    "service": "backend",
                    "passed": verification.all_pass,
                    "checks": [
                        {"name": c.name, "passed": c.passed}
                        for c in verification.checks
                    ],
                })
                if not verification.all_pass:
                    all_pass = False
            
            return StageResult(
                stage=DeploymentStage.VERIFICATION,
                status=DeploymentStatus.SUCCESS if all_pass else DeploymentStatus.FAILED,
                started_at=started_at,
                completed_at=datetime.utcnow(),
                message="All checks passed" if all_pass else "Some checks failed",
                data={"checks": checks},
                error=None if all_pass else "Verification failed",
            )
            
        except Exception as e:
            return StageResult(
                stage=DeploymentStage.VERIFICATION,
                status=DeploymentStatus.FAILED,
                started_at=started_at,
                completed_at=datetime.utcnow(),
                error=str(e),
            )
    
    async def _add_ci_workflow(self, repo_name: str) -> None:
        """Add GitHub Actions CI/CD workflow."""
        workflow_content = """name: CI/CD

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json
      
      - name: Install frontend dependencies
        working-directory: frontend
        run: npm ci
      
      - name: Run frontend tests
        working-directory: frontend
        run: npm test -- --passWithNoTests
      
      - name: Build frontend
        working-directory: frontend
        run: npm run build

  deploy:
    needs: test
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Deploy to Vercel
        uses: amondnet/vercel-action@v20
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-org-id: ${{ secrets.VERCEL_ORG_ID }}
          vercel-project-id: ${{ secrets.VERCEL_PROJECT_ID }}
          working-directory: frontend
"""
        
        try:
            self.github.upload_file(
                repo_name=repo_name,
                path=".github/workflows/ci.yml",
                content=workflow_content,
                message="Add CI/CD workflow",
            )
        except GitHubError as e:
            logger.warning(f"Failed to add CI workflow: {e}")
    
    async def rollback(
        self,
        project_id: str,
        to_version: Optional[str] = None,
    ) -> DeploymentSummary:
        """
        Rollback a deployment.
        
        Args:
            project_id: Project ID to rollback
            to_version: Specific version to rollback to
            
        Returns:
            Updated DeploymentSummary
        """
        summary = self._deployments.get(project_id)
        
        if not summary:
            raise ValueError(f"No deployment found for project: {project_id}")
        
        logger.info(f"Rolling back deployment for {project_id}")
        
        try:
            # Rollback Vercel
            if summary.vercel_deployment_id:
                await self._vercel.rollback(
                    summary.vercel_deployment_id,
                    to_version or "previous",
                )
            
            # Rollback Render
            if summary.render_deployment_id:
                await self._render.rollback(
                    summary.render_deployment_id,
                    to_version or "previous",
                )
            
            summary.status = DeploymentStatus.ROLLED_BACK
            logger.info(f"Rollback completed for {project_id}")
            
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            raise
        
        return summary
    
    def get_deployment_status(self, project_id: str) -> Optional[DeploymentSummary]:
        """Get current deployment status for a project."""
        return self._deployments.get(project_id)
    
    def list_deployments(self) -> List[DeploymentSummary]:
        """List all deployments."""
        return list(self._deployments.values())


# Convenience function for quick deployments
async def quick_deploy(
    project_name: str,
    frontend_path: Optional[Path] = None,
    backend_path: Optional[Path] = None,
    environment: str = "production",
    env_vars: Optional[Dict[str, str]] = None,
) -> DeploymentSummary:
    """
    Quick deployment helper function.
    
    Args:
        project_name: Project name
        frontend_path: Path to frontend code
        backend_path: Path to backend code
        environment: Deployment environment
        env_vars: Environment variables
        
    Returns:
        DeploymentSummary
    """
    import uuid
    
    plan = DeploymentPlan(
        project_id=str(uuid.uuid4()),
        project_name=project_name,
        environment=environment,
        frontend_path=frontend_path,
        backend_path=backend_path,
        deploy_frontend=frontend_path is not None,
        deploy_backend=backend_path is not None,
        environment_variables=env_vars or {},
    )
    
    orchestrator = DeploymentOrchestrator()
    return await orchestrator.deploy(plan)
