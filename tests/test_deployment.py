"""
Tests for deployment module.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from datetime import timezone, datetime
from pathlib import Path
import tempfile
import os

try:
    from src.deployment.github import (
        GitHubClient,
        GitHubRepo,
        GitHubWorkflow,
        WorkflowRun,
        GitHubError,
        RepositoryExistsError,
        AuthenticationError,
    )
except ImportError:
    pytest.skip("PyGithub not installed", allow_module_level=True)
from src.deployment.orchestrator import (
    DeploymentOrchestrator,
    DeploymentPlan,
    DeploymentSummary,
    DeploymentStatus,
    DeploymentStage,
    StageResult,
    quick_deploy,
)


# ============== GitHub Client Tests ==============

class TestGitHubClient:
    """Tests for GitHubClient."""
    
    def test_init_requires_token(self):
        """Test that initialization requires a token."""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(AuthenticationError):
                GitHubClient()
    
    @patch('src.deployment.github.Github')
    def test_init_with_token(self, mock_github):
        """Test initialization with token."""
        mock_user = Mock()
        mock_user.login = "testuser"
        mock_github.return_value.get_user.return_value = mock_user
        
        client = GitHubClient(token="ghp_test123")
        
        assert client.token == "ghp_test123"
        assert client.username == "testuser"
    
    @patch('src.deployment.github.Github')
    def test_create_repository(self, mock_github):
        """Test repository creation."""
        mock_user = Mock()
        mock_user.login = "testuser"
        mock_repo = Mock()
        mock_repo.id = 12345
        mock_repo.name = "test-repo"
        mock_repo.full_name = "testuser/test-repo"
        mock_repo.private = True
        mock_repo.html_url = "https://github.com/testuser/test-repo"
        mock_repo.clone_url = "https://github.com/testuser/test-repo.git"
        mock_repo.ssh_url = "git@github.com:testuser/test-repo.git"
        mock_repo.default_branch = "main"
        mock_repo.created_at = datetime(2024, 1, 1)
        mock_repo.description = "Test repo"
        
        mock_user.create_repo.return_value = mock_repo
        mock_github.return_value.get_user.return_value = mock_user
        
        client = GitHubClient(token="ghp_test123")
        repo = client.create_repository("test-repo", description="Test repo")
        
        assert repo.name == "test-repo"
        assert repo.full_name == "testuser/test-repo"
        assert repo.private is True
    
    @patch('src.deployment.github.Github')
    def test_get_repository(self, mock_github):
        """Test getting a repository."""
        mock_user = Mock()
        mock_user.login = "testuser"
        
        mock_repo = Mock()
        mock_repo.id = 12345
        mock_repo.name = "test-repo"
        mock_repo.full_name = "testuser/test-repo"
        mock_repo.private = False
        mock_repo.html_url = "https://github.com/testuser/test-repo"
        mock_repo.clone_url = "https://github.com/testuser/test-repo.git"
        mock_repo.ssh_url = "git@github.com:testuser/test-repo.git"
        mock_repo.default_branch = "main"
        mock_repo.created_at = datetime(2024, 1, 1)
        mock_repo.description = None
        
        mock_github.return_value.get_user.return_value = mock_user
        mock_github.return_value.get_repo.return_value = mock_repo
        
        client = GitHubClient(token="ghp_test123")
        repo = client.get_repository("testuser/test-repo")
        
        assert repo.full_name == "testuser/test-repo"
    
    @patch('src.deployment.github.Github')
    def test_delete_repository(self, mock_github):
        """Test deleting a repository."""
        mock_user = Mock()
        mock_user.login = "testuser"
        mock_repo = Mock()
        
        mock_github.return_value.get_user.return_value = mock_user
        mock_github.return_value.get_repo.return_value = mock_repo
        
        client = GitHubClient(token="ghp_test123")
        result = client.delete_repository("testuser/test-repo")
        
        assert result is True
        mock_repo.delete.assert_called_once()


class TestGitHubRepo:
    """Tests for GitHubRepo dataclass."""
    
    def test_to_dict(self):
        """Test serialization to dictionary."""
        repo = GitHubRepo(
            id=12345,
            name="test-repo",
            full_name="user/test-repo",
            private=True,
            html_url="https://github.com/user/test-repo",
            clone_url="https://github.com/user/test-repo.git",
            ssh_url="git@github.com:user/test-repo.git",
            default_branch="main",
            created_at=datetime(2024, 1, 1),
            description="Test repository",
        )
        
        data = repo.to_dict()
        
        assert data["name"] == "test-repo"
        assert data["private"] is True
        assert "html_url" in data


class TestWorkflowRun:
    """Tests for WorkflowRun dataclass."""
    
    def test_is_success(self):
        """Test success check."""
        run = WorkflowRun(
            id=1,
            name="CI",
            status="completed",
            conclusion="success",
            html_url="https://github.com/...",
            created_at=datetime.now(timezone.utc),
        )
        
        assert run.is_success is True
        assert run.is_running is False
    
    def test_is_running(self):
        """Test running check."""
        run = WorkflowRun(
            id=1,
            name="CI",
            status="in_progress",
            conclusion=None,
            html_url="https://github.com/...",
            created_at=datetime.now(timezone.utc),
        )
        
        assert run.is_running is True
        assert run.is_success is False


# ============== Deployment Orchestrator Tests ==============

class TestDeploymentPlan:
    """Tests for DeploymentPlan."""
    
    def test_default_values(self):
        """Test default plan values."""
        plan = DeploymentPlan(
            project_id="proj_123",
            project_name="test-project",
            environment="production",
        )
        
        assert plan.deploy_frontend is True
        assert plan.deploy_backend is True
        assert plan.create_github_repo is True
        assert plan.github_private is True


class TestDeploymentSummary:
    """Tests for DeploymentSummary."""
    
    def test_to_dict(self):
        """Test serialization."""
        summary = DeploymentSummary(
            project_id="proj_123",
            project_name="test-project",
            status=DeploymentStatus.SUCCESS,
            started_at=datetime(2024, 1, 1, 12, 0),
            completed_at=datetime(2024, 1, 1, 12, 5),
            github_url="https://github.com/user/test-project",
            frontend_url="https://test-project.vercel.app",
            backend_url="https://test-project.onrender.com",
        )
        
        data = summary.to_dict()
        
        assert data["project_id"] == "proj_123"
        assert data["status"] == "success"
        assert data["urls"]["frontend"] == "https://test-project.vercel.app"


class TestStageResult:
    """Tests for StageResult."""
    
    def test_success_result(self):
        """Test successful stage result."""
        result = StageResult(
            stage=DeploymentStage.GITHUB_REPO,
            status=DeploymentStatus.SUCCESS,
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            message="Repository created",
            data={"full_name": "user/repo"},
        )
        
        assert result.status == DeploymentStatus.SUCCESS
        assert result.error is None
    
    def test_failed_result(self):
        """Test failed stage result."""
        result = StageResult(
            stage=DeploymentStage.FRONTEND_DEPLOY,
            status=DeploymentStatus.FAILED,
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            error="Build failed",
        )
        
        assert result.status == DeploymentStatus.FAILED
        assert result.error == "Build failed"


class TestDeploymentOrchestrator:
    """Tests for DeploymentOrchestrator."""
    
    def test_initialization(self):
        """Test orchestrator initialization."""
        with patch.dict('os.environ', {
            'GITHUB_TOKEN': 'ghp_test',
            'VERCEL_TOKEN': 'vercel_test',
            'RENDER_TOKEN': 'render_test',
        }):
            orchestrator = DeploymentOrchestrator()
            
            assert orchestrator.github_token == 'ghp_test'
            assert orchestrator.vercel_token == 'vercel_test'
            assert orchestrator.render_token == 'render_test'
    
    def test_initialization_with_explicit_tokens(self):
        """Test initialization with explicit tokens."""
        orchestrator = DeploymentOrchestrator(
            github_token="custom_github",
            vercel_token="custom_vercel",
            render_token="custom_render",
        )
        
        assert orchestrator.github_token == "custom_github"
        assert orchestrator.vercel_token == "custom_vercel"
        assert orchestrator.render_token == "custom_render"
    
    @pytest.mark.asyncio
    async def test_deploy_creates_summary(self):
        """Test that deploy creates a summary."""
        orchestrator = DeploymentOrchestrator(
            github_token="test",
            vercel_token="test",
            render_token="test",
        )
        
        # Mock the GitHub client
        with patch.object(orchestrator, '_github') as mock_github:
            mock_github.create_repository.return_value = GitHubRepo(
                id=1,
                name="test",
                full_name="user/test",
                private=True,
                html_url="https://github.com/user/test",
                clone_url="https://github.com/user/test.git",
                ssh_url="git@github.com:user/test.git",
                default_branch="main",
                created_at=datetime.now(timezone.utc),
            )
            mock_github.upload_directory.return_value = {"uploaded": 0, "files": [], "errors": []}
            mock_github.upload_file.return_value = {"commit_sha": "abc123"}
            mock_github.set_repository_secrets.return_value = {}
            
            # Mock providers
            with patch.object(orchestrator._vercel, 'deploy', new_callable=AsyncMock) as mock_vercel:
                with patch.object(orchestrator._render, 'deploy', new_callable=AsyncMock) as mock_render:
                    with patch.object(orchestrator._vercel, 'verify_deployment', new_callable=AsyncMock) as mock_verify_v:
                        with patch.object(orchestrator._render, 'verify_deployment', new_callable=AsyncMock) as mock_verify_r:
                            # Configure mocks
                            from src.deployment.models import DeploymentResult, VerificationReport, VerificationCheck
                            
                            mock_vercel.return_value = DeploymentResult(
                                success=True,
                                deployment_id="dpl_123",
                                provider="vercel",
                                environment="production",
                                frontend_url="https://test.vercel.app",
                            )
                            
                            mock_render.return_value = DeploymentResult(
                                success=True,
                                deployment_id="srv_123",
                                provider="render",
                                environment="production",
                                backend_url="https://test.onrender.com",
                            )
                            
                            mock_verify_v.return_value = VerificationReport(
                                all_pass=True,
                                checks=[VerificationCheck(name="Health", passed=True)],
                            )
                            
                            mock_verify_r.return_value = VerificationReport(
                                all_pass=True,
                                checks=[VerificationCheck(name="Health", passed=True)],
                            )
                            
                            with tempfile.TemporaryDirectory() as tmpdir:
                                plan = DeploymentPlan(
                                    project_id="proj_123",
                                    project_name="test-project",
                                    environment="production",
                                    frontend_path=Path(tmpdir),
                                    backend_path=Path(tmpdir),
                                )
                                
                                # Set up the github property to return our mock
                                type(orchestrator).github = property(lambda self: mock_github)
                                
                                summary = await orchestrator.deploy(plan)
                                
                                assert summary.project_id == "proj_123"
                                assert len(summary.stages) > 0
    
    def test_get_deployment_status(self):
        """Test getting deployment status."""
        orchestrator = DeploymentOrchestrator(
            github_token="test",
            vercel_token="test",
            render_token="test",
        )
        
        # No deployment yet
        assert orchestrator.get_deployment_status("unknown") is None
        
        # Add a deployment
        summary = DeploymentSummary(
            project_id="proj_123",
            project_name="test",
            status=DeploymentStatus.SUCCESS,
            started_at=datetime.now(timezone.utc),
        )
        orchestrator._deployments["proj_123"] = summary
        
        assert orchestrator.get_deployment_status("proj_123") == summary
    
    def test_list_deployments(self):
        """Test listing all deployments."""
        orchestrator = DeploymentOrchestrator(
            github_token="test",
            vercel_token="test",
            render_token="test",
        )
        
        # Empty initially
        assert len(orchestrator.list_deployments()) == 0
        
        # Add deployments
        orchestrator._deployments["proj_1"] = DeploymentSummary(
            project_id="proj_1",
            project_name="test1",
            status=DeploymentStatus.SUCCESS,
            started_at=datetime.now(timezone.utc),
        )
        orchestrator._deployments["proj_2"] = DeploymentSummary(
            project_id="proj_2",
            project_name="test2",
            status=DeploymentStatus.IN_PROGRESS,
            started_at=datetime.now(timezone.utc),
        )
        
        assert len(orchestrator.list_deployments()) == 2


class TestDeploymentStatus:
    """Tests for DeploymentStatus enum."""
    
    def test_status_values(self):
        """Test all status values exist."""
        assert DeploymentStatus.PENDING.value == "pending"
        assert DeploymentStatus.IN_PROGRESS.value == "in_progress"
        assert DeploymentStatus.SUCCESS.value == "success"
        assert DeploymentStatus.FAILED.value == "failed"
        assert DeploymentStatus.ROLLED_BACK.value == "rolled_back"


class TestDeploymentStage:
    """Tests for DeploymentStage enum."""
    
    def test_stage_values(self):
        """Test all stage values exist."""
        assert DeploymentStage.GITHUB_REPO.value == "github_repo"
        assert DeploymentStage.FRONTEND_DEPLOY.value == "frontend_deploy"
        assert DeploymentStage.BACKEND_DEPLOY.value == "backend_deploy"
        assert DeploymentStage.ENVIRONMENT_CONFIG.value == "environment_config"
        assert DeploymentStage.VERIFICATION.value == "verification"
