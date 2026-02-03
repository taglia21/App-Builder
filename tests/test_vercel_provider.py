"""Tests for Vercel deployment provider."""
import pytest
from unittest.mock import Mock, AsyncMock, patch, mock_open
from pathlib import Path
import tempfile
import json

from src.deployment.providers.vercel import VercelProvider
from src.deployment.models import DeploymentConfig, DeploymentResult, VerificationReport


class TestVercelProvider:
    """Test VercelProvider implementation."""

    @pytest.fixture
    def provider(self):
        """Create a VercelProvider instance."""
        return VercelProvider()

    @pytest.fixture
    def deployment_config(self):
        """Create a test deployment configuration."""
        return DeploymentConfig(
            provider="vercel",
            environment="production",
            region="us-east-1"
        )

    @pytest.fixture
    def temp_codebase(self):
        """Create a temporary codebase directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.mark.asyncio
    async def test_check_prerequisites(self, provider):
        """Test prerequisite checking."""
        result = await provider.check_prerequisites()
        
        assert isinstance(result, dict)
        assert "cli_installed" in result
        assert "auth_token_present" in result

    def test_validate_config_valid(self, provider, deployment_config):
        """Test config validation with valid config."""
        is_valid, error = provider.validate_config(deployment_config)
        
        assert is_valid is True
        assert error == ""

    def test_validate_config_invalid_provider(self, provider, deployment_config):
        """Test config validation with invalid provider."""
        deployment_config.provider = "aws"
        
        is_valid, error = provider.validate_config(deployment_config)
        
        assert is_valid is False
        assert "vercel" in error.lower()

    @pytest.mark.asyncio
    async def test_deploy_success(self, provider, temp_codebase, deployment_config):
        """Test successful deployment."""
        secrets = {"VERCEL_TOKEN": "test_token"}
        
        result = await provider.deploy(temp_codebase, deployment_config, secrets)
        
        assert isinstance(result, DeploymentResult)
        assert result.success is True
        assert result.provider == "vercel"
        assert result.deployment_id.startswith("dpl_vercel_")
        assert "vercel.app" in result.frontend_url
        assert isinstance(result.logs, list)
        assert len(result.logs) > 0

    @pytest.mark.asyncio
    async def test_deploy_generates_vercel_config(self, provider, temp_codebase, deployment_config):
        """Test that deployment generates vercel.json."""
        secrets = {"VERCEL_TOKEN": "test_token"}
        
        await provider.deploy(temp_codebase, deployment_config, secrets)
        
        vercel_config_path = temp_codebase / "vercel.json"
        assert vercel_config_path.exists()
        
        with open(vercel_config_path, 'r') as f:
            config = json.load(f)
        
        assert config["framework"] == "nextjs"
        assert config["buildCommand"] == "npm run build"
        assert deployment_config.region in config["regions"]

    @pytest.mark.asyncio
    async def test_verify_deployment(self, provider):
        """Test deployment verification."""
        deployment_id = "dpl_vercel_12345"
        
        report = await provider.verify_deployment(deployment_id)
        
        assert isinstance(report, VerificationReport)
        assert report.all_pass is True
        assert len(report.checks) > 0
        assert any(check.name == "Frontend Accessible" for check in report.checks)
        assert any(check.name == "SSL Valid" for check in report.checks)

    @pytest.mark.asyncio
    async def test_rollback(self, provider):
        """Test deployment rollback."""
        deployment_id = "dpl_vercel_current"
        rollback_to_id = "dpl_vercel_previous"
        
        result = await provider.rollback(deployment_id, rollback_to_id)
        
        assert result is True

    @pytest.mark.asyncio
    async def test_sync_secrets(self, provider):
        """Test secret synchronization."""
        secrets = {
            "API_KEY": "secret123",
            "DATABASE_URL": "postgres://..."
        }
        
        # Should not raise an exception
        await provider._sync_secrets(secrets)

    def test_generate_vercel_config(self, provider, temp_codebase, deployment_config):
        """Test vercel.json generation."""
        provider._generate_vercel_config(temp_codebase, deployment_config)
        
        config_path = temp_codebase / "vercel.json"
        assert config_path.exists()
        
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        assert "buildCommand" in config
        assert "installCommand" in config
        assert "framework" in config
        assert "regions" in config

    @pytest.mark.asyncio
    async def test_deployment_result_structure(self, provider, temp_codebase, deployment_config):
        """Test that deployment result has all required fields."""
        secrets = {"VERCEL_TOKEN": "test_token"}
        
        result = await provider.deploy(temp_codebase, deployment_config, secrets)
        
        # Check all required fields
        assert hasattr(result, 'success')
        assert hasattr(result, 'deployment_id')
        assert hasattr(result, 'provider')
        assert hasattr(result, 'environment')
        assert hasattr(result, 'frontend_url')
        assert hasattr(result, 'logs')
        assert hasattr(result, 'duration_seconds')
        
        # Verify types
        assert isinstance(result.success, bool)
        assert isinstance(result.deployment_id, str)
        assert isinstance(result.logs, list)
        assert isinstance(result.duration_seconds, (int, float))

    @pytest.mark.asyncio
    async def test_verification_report_structure(self, provider):
        """Test that verification report has all required fields."""
        report = await provider.verify_deployment("dpl_test")
        
        assert hasattr(report, 'all_pass')
        assert hasattr(report, 'checks')
        assert isinstance(report.all_pass, bool)
        assert isinstance(report.checks, list)
        
        # Check each verification check
        for check in report.checks:
            assert hasattr(check, 'name')
            assert hasattr(check, 'passed')
            assert isinstance(check.passed, bool)

    @pytest.mark.asyncio
    async def test_deployment_with_different_regions(self, provider, temp_codebase):
        """Test deployment with different region configurations."""
        regions = ["us-east-1", "eu-west-1", "ap-southeast-1"]
        
        for region in regions:
            config = DeploymentConfig(
                provider="vercel",
                environment="production",
                region=region
            )
            
            result = await provider.deploy(temp_codebase, config, {})
            assert result.success is True
            
            # Verify region in config file
            with open(temp_codebase / "vercel.json", 'r') as f:
                vercel_config = json.load(f)
            assert region in vercel_config["regions"]

    @pytest.mark.asyncio
    async def test_deployment_without_secrets(self, provider, temp_codebase, deployment_config):
        """Test deployment without providing secrets."""
        result = await provider.deploy(temp_codebase, deployment_config, {})
        
        # Should still succeed (mock deployment)
        assert result.success is True

    def test_validate_multiple_configs(self, provider):
        """Test validation of various config scenarios."""
        # Valid config
        valid_config = DeploymentConfig(provider="vercel", environment="production", region="us-east-1")
        is_valid, _ = provider.validate_config(valid_config)
        assert is_valid is True
        
        # Invalid provider
        invalid_config = DeploymentConfig(provider="netlify", environment="production", region="us-east-1")
        is_valid, error = provider.validate_config(invalid_config)
        assert is_valid is False
        assert error != ""
