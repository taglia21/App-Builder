"""
Tests for the Dashboard Module

Tests for FastAPI + HTMX dashboard functionality.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient


# ==================== Test API Models ====================

class TestAPIModels:
    """Tests for API request/response models."""
    
    def test_project_create_model(self):
        """Test ProjectCreate validation."""
        from src.dashboard.api import ProjectCreate
        
        project = ProjectCreate(
            name="Test App",
            description="This is a test application with enough characters",
        )
        assert project.name == "Test App"
        assert project.description == "This is a test application with enough characters"
        assert project.features is None
        assert project.tech_stack is None
    
    def test_project_create_with_optional_fields(self):
        """Test ProjectCreate with optional fields."""
        from src.dashboard.api import ProjectCreate
        
        project = ProjectCreate(
            name="Test App",
            description="This is a test application with enough characters",
            features=["auth", "billing"],
            tech_stack={"frontend": "nextjs", "backend": "fastapi"},
        )
        assert project.features == ["auth", "billing"]
        assert project.tech_stack == {"frontend": "nextjs", "backend": "fastapi"}
    
    def test_project_response_model(self):
        """Test ProjectResponse model."""
        from src.dashboard.api import ProjectResponse, ProjectStatus
        
        response = ProjectResponse(
            id="proj_123",
            name="My App",
            description="A cool app",
            status=ProjectStatus.DEPLOYED,
            features=["auth"],
            tech_stack={"frontend": "nextjs"},
            urls={"frontend": "https://example.com"},
            created_at=datetime(2024, 1, 15),
            updated_at=datetime(2024, 1, 16),
        )
        assert response.id == "proj_123"
        assert response.status == ProjectStatus.DEPLOYED
    
    def test_project_status_enum(self):
        """Test ProjectStatus enum values."""
        from src.dashboard.api import ProjectStatus
        
        assert ProjectStatus.DRAFT == "draft"
        assert ProjectStatus.GENERATING == "generating"
        assert ProjectStatus.READY == "ready"
        assert ProjectStatus.DEPLOYING == "deploying"
        assert ProjectStatus.DEPLOYED == "deployed"
        assert ProjectStatus.FAILED == "failed"
    
    def test_generation_status_model(self):
        """Test GenerationStatus model."""
        from src.dashboard.api import GenerationStatus
        
        status = GenerationStatus(
            project_id="proj_123",
            status="in_progress",
            progress=50,
            current_step="Writing code",
            steps=[{"name": "Step 1", "status": "complete"}],
            estimated_time_remaining=60,
        )
        assert status.progress == 50
        assert status.estimated_time_remaining == 60
    
    def test_deployment_status_model(self):
        """Test DeploymentStatus model."""
        from src.dashboard.api import DeploymentStatus
        
        status = DeploymentStatus(
            project_id="proj_123",
            deployment_id="dpl_456",
            status="deployed",
            urls={"frontend": "https://app.example.com"},
            started_at=datetime(2024, 1, 15, 12, 0),
            completed_at=datetime(2024, 1, 15, 12, 5),
        )
        assert status.deployment_id == "dpl_456"
        assert status.completed_at is not None
    
    def test_subscription_info_model(self):
        """Test SubscriptionInfo model."""
        from src.dashboard.api import SubscriptionInfo
        
        info = SubscriptionInfo(
            tier="pro",
            status="active",
            apps_used=2,
            apps_limit=5,
            billing_period="monthly",
            next_billing_date=datetime(2024, 2, 1),
            amount=2900,
        )
        assert info.tier == "pro"
        assert info.amount == 2900
    
    def test_api_key_response_model(self):
        """Test APIKeyResponse model."""
        from src.dashboard.api import APIKeyResponse
        
        response = APIKeyResponse(
            id="key_123",
            name="Production Key",
            key="lf_abc123",
            scopes=["read", "write"],
            created_at=datetime.utcnow(),
        )
        assert response.id == "key_123"
        assert response.key == "lf_abc123"


# ==================== Test API Routes ====================

class TestAPIRoutes:
    """Tests for API route handlers."""
    
    @pytest.fixture
    def api_routes(self):
        """Create API routes instance."""
        from src.dashboard.api import APIRoutes
        return APIRoutes()
    
    @pytest.mark.asyncio
    async def test_list_projects(self, api_routes):
        """Test listing projects."""
        result = await api_routes.list_projects()
        assert result.total >= 0
        assert result.page == 1
        assert result.per_page == 10
    
    @pytest.mark.asyncio
    async def test_list_projects_with_pagination(self, api_routes):
        """Test listing projects with pagination."""
        result = await api_routes.list_projects(page=2, per_page=5)
        assert result.page == 2
        assert result.per_page == 5
    
    @pytest.mark.asyncio
    async def test_get_project(self, api_routes):
        """Test getting a single project."""
        result = await api_routes.get_project("proj_123")
        assert result.id == "proj_123"
        assert result.name is not None
    
    @pytest.mark.asyncio
    async def test_create_project(self, api_routes):
        """Test creating a project."""
        from src.dashboard.api import ProjectCreate, ProjectStatus
        
        project = ProjectCreate(
            name="New Test App",
            description="A new test application with sufficient description",
            features=["auth", "billing"],
        )
        result = await api_routes.create_project(project)
        assert result.name == "New Test App"
        assert result.status == ProjectStatus.DRAFT
        assert result.features == ["auth", "billing"]
    
    @pytest.mark.asyncio
    async def test_update_project(self, api_routes):
        """Test updating a project."""
        from src.dashboard.api import ProjectUpdate
        
        updates = ProjectUpdate(name="Updated Name")
        result = await api_routes.update_project("proj_123", updates)
        assert result.id == "proj_123"
    
    @pytest.mark.asyncio
    async def test_delete_project(self, api_routes):
        """Test deleting a project."""
        result = await api_routes.delete_project("proj_123")
        assert result["deleted"] is True
        assert result["project_id"] == "proj_123"
    
    @pytest.mark.asyncio
    async def test_start_generation(self, api_routes):
        """Test starting code generation."""
        from src.dashboard.api import GenerationRequest
        
        request = GenerationRequest(project_id="proj_123")
        result = await api_routes.start_generation(request)
        assert result.project_id == "proj_123"
        assert result.status == "in_progress"
        assert len(result.steps) > 0
    
    @pytest.mark.asyncio
    async def test_get_generation_status(self, api_routes):
        """Test getting generation status."""
        result = await api_routes.get_generation_status("proj_123")
        assert result.project_id == "proj_123"
        assert 0 <= result.progress <= 100
    
    @pytest.mark.asyncio
    async def test_start_deployment(self, api_routes):
        """Test starting deployment."""
        from src.dashboard.api import DeploymentRequest
        
        request = DeploymentRequest(project_id="proj_123")
        result = await api_routes.start_deployment(request)
        assert result.project_id == "proj_123"
        assert result.deployment_id is not None
    
    @pytest.mark.asyncio
    async def test_get_deployment_status(self, api_routes):
        """Test getting deployment status."""
        result = await api_routes.get_deployment_status("proj_123", "dpl_456")
        assert result.project_id == "proj_123"
        assert result.deployment_id == "dpl_456"
    
    @pytest.mark.asyncio
    async def test_get_subscription(self, api_routes):
        """Test getting subscription info."""
        result = await api_routes.get_subscription()
        assert result.tier in ["free", "pro", "enterprise"]
        assert result.apps_used >= 0
    
    @pytest.mark.asyncio
    async def test_create_checkout_session(self, api_routes):
        """Test creating checkout session."""
        result = await api_routes.create_checkout_session(tier="pro")
        assert "checkout_url" in result
        assert "session_id" in result
    
    @pytest.mark.asyncio
    async def test_create_portal_session(self, api_routes):
        """Test creating portal session."""
        result = await api_routes.create_portal_session()
        assert "portal_url" in result
    
    @pytest.mark.asyncio
    async def test_list_api_keys(self, api_routes):
        """Test listing API keys."""
        result = await api_routes.list_api_keys()
        assert isinstance(result, list)
    
    @pytest.mark.asyncio
    async def test_create_api_key(self, api_routes):
        """Test creating an API key."""
        from src.dashboard.api import APIKeyCreate
        
        request = APIKeyCreate(name="Test Key", scopes=["read"])
        result = await api_routes.create_api_key(request)
        assert result.name == "Test Key"
        assert result.key.startswith("lf_")
        assert result.scopes == ["read"]
    
    @pytest.mark.asyncio
    async def test_revoke_api_key(self, api_routes):
        """Test revoking an API key."""
        result = await api_routes.revoke_api_key("key_123")
        assert result["revoked"] is True
        assert result["key_id"] == "key_123"


class TestAPIRouter:
    """Tests for the API router factory."""
    
    def test_create_api_router(self):
        """Test creating API router."""
        from src.dashboard.api import create_api_router
        
        router = create_api_router()
        assert router is not None
        
        # Check that routes are registered
        route_paths = [route.path for route in router.routes]
        assert "/projects" in route_paths
        assert "/projects/{project_id}" in route_paths
        assert "/generate" in route_paths
        assert "/deploy" in route_paths
        assert "/subscription" in route_paths
        assert "/api-keys" in route_paths


# ==================== Test Dashboard Routes ====================

class TestDashboardRoutes:
    """Tests for dashboard HTML routes."""
    
    @pytest.fixture
    def mock_templates(self):
        """Create mock templates."""
        templates = Mock()
        templates.TemplateResponse = Mock(return_value="<html>Mock</html>")
        return templates
    
    @pytest.fixture
    def mock_request(self):
        """Create mock request."""
        request = Mock()
        request.url = Mock()
        request.url.path = "/dashboard"
        return request
    
    def test_dashboard_routes_initialization(self, mock_templates):
        """Test DashboardRoutes initialization."""
        from src.dashboard.routes import DashboardRoutes
        
        routes = DashboardRoutes(mock_templates)
        assert routes.templates == mock_templates
    
    @pytest.mark.asyncio
    async def test_home_route(self, mock_templates, mock_request):
        """Test home page route."""
        from src.dashboard.routes import DashboardRoutes
        
        routes = DashboardRoutes(mock_templates)
        result = await routes.home(mock_request)
        
        mock_templates.TemplateResponse.assert_called()
        call_args = mock_templates.TemplateResponse.call_args
        assert "pages/landing.html" in str(call_args)
    
    @pytest.mark.asyncio
    async def test_dashboard_route(self, mock_templates, mock_request):
        """Test dashboard page route."""
        from src.dashboard.routes import DashboardRoutes
        
        routes = DashboardRoutes(mock_templates)
        result = await routes.dashboard(mock_request)
        
        mock_templates.TemplateResponse.assert_called()
        call_args = mock_templates.TemplateResponse.call_args
        assert "pages/dashboard.html" in str(call_args)
    
    @pytest.mark.asyncio
    async def test_new_project_route(self, mock_templates, mock_request):
        """Test new project page route."""
        from src.dashboard.routes import DashboardRoutes
        
        routes = DashboardRoutes(mock_templates)
        result = await routes.new_project(mock_request)
        
        mock_templates.TemplateResponse.assert_called()
        call_args = mock_templates.TemplateResponse.call_args
        assert "pages/new_project.html" in str(call_args)
    
    @pytest.mark.asyncio
    async def test_settings_route(self, mock_templates, mock_request):
        """Test settings page route."""
        from src.dashboard.routes import DashboardRoutes
        
        routes = DashboardRoutes(mock_templates)
        result = await routes.settings(mock_request)
        
        mock_templates.TemplateResponse.assert_called()
        call_args = mock_templates.TemplateResponse.call_args
        assert "pages/settings.html" in str(call_args)
    
    @pytest.mark.asyncio
    async def test_billing_route(self, mock_templates, mock_request):
        """Test billing page route."""
        from src.dashboard.routes import DashboardRoutes
        
        routes = DashboardRoutes(mock_templates)
        result = await routes.billing(mock_request)
        
        mock_templates.TemplateResponse.assert_called()
        call_args = mock_templates.TemplateResponse.call_args
        assert "pages/billing.html" in str(call_args)


class TestDashboardRouter:
    """Tests for the dashboard router factory."""
    
    def test_create_dashboard_router(self):
        """Test creating dashboard router."""
        from src.dashboard.routes import create_dashboard_router
        
        templates = Mock()
        router = create_dashboard_router(templates)
        assert router is not None
        
        # Check that routes are registered
        route_paths = [route.path for route in router.routes]
        assert "/" in route_paths
        assert "/dashboard" in route_paths
        assert "/projects/new" in route_paths


# ==================== Test Dashboard App ====================

class TestDashboardApp:
    """Tests for the DashboardApp class."""
    
    def test_dashboard_app_creation(self):
        """Test creating DashboardApp."""
        from src.dashboard.app import DashboardApp
        
        app = DashboardApp()
        assert app.title == "NexusAI"
        assert app.app is not None
    
    def test_dashboard_app_with_custom_title(self):
        """Test creating DashboardApp with custom title."""
        from src.dashboard.app import DashboardApp
        
        app = DashboardApp(title="Custom App")
        assert app.title == "Custom App"
    
    def test_dashboard_app_is_fastapi(self):
        """Test that DashboardApp creates a FastAPI app."""
        from src.dashboard.app import DashboardApp
        
        app = DashboardApp()
        assert isinstance(app.app, FastAPI)
    
    def test_create_app_factory(self):
        """Test create_app factory function."""
        from src.dashboard.app import create_app
        
        app = create_app()
        assert isinstance(app, FastAPI)


# ==================== Integration Tests ====================

class TestDashboardIntegration:
    """Integration tests for the dashboard."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        from src.dashboard.app import create_app
        app = create_app()
        return TestClient(app)
    
    def test_home_page(self, client):
        """Test home page loads."""
        response = client.get("/")
        # May redirect or return HTML
        assert response.status_code in [200, 307, 303]
    
    def test_dashboard_page(self, client):
        """Test dashboard page loads."""
        response = client.get("/dashboard")
        assert response.status_code in [200, 307, 303]


# ==================== Run Tests ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
