"""
Unit tests for Enhanced README Generator.

Tests cover:
- README section generation
- Architecture diagrams
- API documentation
- Feature flags integration
"""

import pytest
from datetime import datetime

from src.utils.readme_generator import (
    generate_enhanced_readme,
    _generate_header,
    _generate_quick_start,
    _generate_architecture,
    _generate_features,
    _generate_api_docs,
    _generate_project_structure,
    _generate_env_vars,
    _generate_local_dev,
    _generate_deployment_guide,
    _generate_tech_stack,
    _generate_testing_guide,
    _generate_contributing,
    _generate_footer,
)


class TestGenerateEnhancedReadme:
    """Tests for main generate_enhanced_readme function."""
    
    @pytest.fixture
    def sample_entity(self):
        """Create a sample entity configuration."""
        return {
            "name": "Task",
            "lower": "task",
            "fields": [
                {"name": "title", "python_type": "str", "required": True},
                {"name": "description", "python_type": "str", "required": False},
                {"name": "completed", "python_type": "bool", "required": True},
            ]
        }
    
    @pytest.fixture
    def sample_features(self):
        """Create sample feature flags."""
        return {
            "needs_payments": True,
            "needs_background_jobs": True,
            "needs_ai_integration": True,
            "needs_email": True,
        }
    
    def test_generates_readme(self, sample_entity, sample_features):
        """Test that function generates a README string."""
        readme = generate_enhanced_readme(
            app_name="Task Manager",
            description="A task management application",
            entity=sample_entity,
            features=sample_features,
        )
        
        assert isinstance(readme, str)
        assert len(readme) > 1000  # Should be substantial
    
    def test_includes_app_name(self, sample_entity, sample_features):
        """Test README includes app name in header."""
        readme = generate_enhanced_readme(
            app_name="My Awesome App",
            description="Description here",
            entity=sample_entity,
            features=sample_features,
        )
        
        assert "My Awesome App" in readme
    
    def test_includes_description(self, sample_entity, sample_features):
        """Test README includes description."""
        readme = generate_enhanced_readme(
            app_name="Test App",
            description="This is a unique description for testing",
            entity=sample_entity,
            features=sample_features,
        )
        
        assert "This is a unique description for testing" in readme
    
    def test_optional_sections(self, sample_entity, sample_features):
        """Test optional sections can be disabled."""
        readme = generate_enhanced_readme(
            app_name="Test App",
            description="Description",
            entity=sample_entity,
            features=sample_features,
            include_architecture=False,
            include_api_docs=False,
            include_deployment=False,
        )
        
        assert isinstance(readme, str)
        # Still should have basic content
        assert "Test App" in readme


class TestGenerateHeader:
    """Tests for header generation."""
    
    def test_header_contains_name(self):
        """Test header contains app name."""
        header = _generate_header("My App", "App description")
        
        assert "# My App" in header
    
    def test_header_contains_description(self):
        """Test header contains description."""
        header = _generate_header("My App", "This is my app description")
        
        assert "This is my app description" in header
    
    def test_header_contains_badges(self):
        """Test header contains badges."""
        header = _generate_header("My App", "Description")
        
        assert "License" in header or "badge" in header.lower()
        assert "Python" in header or "Next.js" in header


class TestGenerateQuickStart:
    """Tests for quick start section generation."""
    
    @pytest.fixture
    def sample_entity(self):
        return {"name": "Item", "lower": "item", "fields": []}
    
    def test_includes_docker_instructions(self, sample_entity):
        """Test quick start includes Docker instructions."""
        quick_start = _generate_quick_start("Test App", sample_entity)
        
        assert "docker" in quick_start.lower()
        assert "docker compose" in quick_start.lower()
    
    def test_includes_manual_setup(self, sample_entity):
        """Test quick start includes manual setup instructions."""
        quick_start = _generate_quick_start("Test App", sample_entity)
        
        assert "pip install" in quick_start or "npm install" in quick_start
    
    def test_includes_verification(self, sample_entity):
        """Test quick start includes verification steps."""
        quick_start = _generate_quick_start("Test App", sample_entity)
        
        assert "localhost" in quick_start
        assert "3000" in quick_start or "8000" in quick_start


class TestGenerateArchitecture:
    """Tests for architecture diagram generation."""
    
    def test_includes_diagram(self):
        """Test architecture section includes ASCII diagram."""
        features = {}
        arch = _generate_architecture("Test App", features)
        
        assert "```" in arch  # Code block for diagram
        assert "Frontend" in arch
        assert "Backend" in arch
    
    def test_includes_celery_when_enabled(self):
        """Test architecture includes Celery when background jobs enabled."""
        features = {"needs_background_jobs": True}
        arch = _generate_architecture("Test App", features)
        
        assert "Celery" in arch or "Background" in arch
    
    def test_includes_ai_when_enabled(self):
        """Test architecture includes AI section when enabled."""
        features = {"needs_ai_integration": True}
        arch = _generate_architecture("Test App", features)
        
        assert "AI" in arch or "ML" in arch
    
    def test_data_flow_section(self):
        """Test architecture includes data flow explanation."""
        features = {}
        arch = _generate_architecture("Test App", features)
        
        assert "Data Flow" in arch or "flow" in arch.lower()


class TestGenerateFeatures:
    """Tests for features section generation."""
    
    def test_always_includes_core_features(self):
        """Test that core features are always included."""
        features = {}
        feature_section = _generate_features(features)
        
        assert "Authentication" in feature_section
        assert "API" in feature_section
    
    def test_includes_payment_when_enabled(self):
        """Test payment feature when enabled."""
        features = {"needs_payments": True}
        feature_section = _generate_features(features)
        
        assert "Payment" in feature_section or "Stripe" in feature_section
    
    def test_includes_background_jobs_when_enabled(self):
        """Test background jobs feature when enabled."""
        features = {"needs_background_jobs": True}
        feature_section = _generate_features(features)
        
        assert "Background" in feature_section or "Celery" in feature_section
    
    def test_includes_ai_when_enabled(self):
        """Test AI feature when enabled."""
        features = {"needs_ai_integration": True}
        feature_section = _generate_features(features)
        
        assert "AI" in feature_section or "🤖" in feature_section


class TestGenerateApiDocs:
    """Tests for API documentation generation."""
    
    @pytest.fixture
    def sample_entity(self):
        return {
            "name": "Product",
            "lower": "product",
            "fields": [
                {"name": "name", "python_type": "str", "required": True},
                {"name": "price", "python_type": "float", "required": True},
            ]
        }
    
    def test_includes_base_url(self, sample_entity):
        """Test API docs include base URL."""
        api_docs = _generate_api_docs(sample_entity)
        
        assert "localhost:8000" in api_docs
    
    def test_includes_auth_endpoints(self, sample_entity):
        """Test API docs include authentication endpoints."""
        api_docs = _generate_api_docs(sample_entity)
        
        assert "/auth/" in api_docs
        assert "login" in api_docs.lower()
    
    def test_includes_entity_endpoints(self, sample_entity):
        """Test API docs include entity CRUD endpoints."""
        api_docs = _generate_api_docs(sample_entity)
        
        assert "product" in api_docs.lower()
        assert "GET" in api_docs
        assert "POST" in api_docs
    
    def test_includes_field_schema(self, sample_entity):
        """Test API docs include field schema."""
        api_docs = _generate_api_docs(sample_entity)
        
        # Should include field names from entity
        assert "name" in api_docs
    
    def test_includes_error_codes(self, sample_entity):
        """Test API docs include error codes."""
        api_docs = _generate_api_docs(sample_entity)
        
        assert "400" in api_docs or "401" in api_docs or "404" in api_docs


class TestGenerateProjectStructure:
    """Tests for project structure section."""
    
    def test_includes_backend_structure(self):
        """Test project structure includes backend folder."""
        entity = {"name": "Item", "lower": "item", "fields": []}
        structure = _generate_project_structure(entity)
        
        assert "backend/" in structure
        assert "main.py" in structure
    
    def test_includes_frontend_structure(self):
        """Test project structure includes frontend folder."""
        entity = {"name": "Item", "lower": "item", "fields": []}
        structure = _generate_project_structure(entity)
        
        assert "frontend/" in structure
    
    def test_includes_entity_files(self):
        """Test project structure references entity files."""
        entity = {"name": "Task", "lower": "task", "fields": []}
        structure = _generate_project_structure(entity)
        
        assert "task" in structure.lower()


class TestGenerateEnvVars:
    """Tests for environment variables section."""
    
    def test_includes_required_vars(self):
        """Test env vars include required variables."""
        features = {}
        env_vars = _generate_env_vars(features)
        
        assert "DATABASE_URL" in env_vars
        assert "SECRET_KEY" in env_vars
    
    def test_includes_payment_vars_when_enabled(self):
        """Test payment env vars when payments enabled."""
        features = {"needs_payments": True}
        env_vars = _generate_env_vars(features)
        
        assert "STRIPE" in env_vars
    
    def test_includes_email_vars_when_enabled(self):
        """Test email env vars when email enabled."""
        features = {"needs_email": True}
        env_vars = _generate_env_vars(features)
        
        assert "SMTP" in env_vars
    
    def test_includes_ai_vars_when_enabled(self):
        """Test AI env vars when AI enabled."""
        features = {"needs_ai_integration": True}
        env_vars = _generate_env_vars(features)
        
        assert "OPENAI" in env_vars


class TestGenerateLocalDev:
    """Tests for local development section."""
    
    def test_includes_backend_setup(self):
        """Test local dev includes backend setup."""
        entity = {"name": "Item", "lower": "item", "fields": []}
        local_dev = _generate_local_dev("Test App", entity)
        
        assert "backend" in local_dev.lower()
        assert "pip install" in local_dev
    
    def test_includes_frontend_setup(self):
        """Test local dev includes frontend setup."""
        entity = {"name": "Item", "lower": "item", "fields": []}
        local_dev = _generate_local_dev("Test App", entity)
        
        assert "frontend" in local_dev.lower()
        assert "npm" in local_dev
    
    def test_includes_db_setup(self):
        """Test local dev includes database setup."""
        entity = {"name": "Item", "lower": "item", "fields": []}
        local_dev = _generate_local_dev("Test App", entity)
        
        assert "DATABASE" in local_dev or "alembic" in local_dev


class TestGenerateDeploymentGuide:
    """Tests for deployment guide section."""
    
    def test_includes_docker_deployment(self):
        """Test deployment includes Docker instructions."""
        deployment = _generate_deployment_guide()
        
        assert "docker" in deployment.lower()
    
    def test_includes_render_deployment(self):
        """Test deployment includes Render instructions."""
        deployment = _generate_deployment_guide()
        
        assert "Render" in deployment or "render" in deployment.lower()
    
    def test_includes_railway_deployment(self):
        """Test deployment includes Railway instructions."""
        deployment = _generate_deployment_guide()
        
        assert "Railway" in deployment or "railway" in deployment.lower()
    
    def test_includes_production_checklist(self):
        """Test deployment includes production checklist."""
        deployment = _generate_deployment_guide()
        
        assert "Checklist" in deployment or "[ ]" in deployment


class TestGenerateTechStack:
    """Tests for tech stack section."""
    
    def test_includes_default_stack(self):
        """Test tech stack includes default technologies."""
        features = {}
        tech_stack = _generate_tech_stack(None, features)
        
        assert "FastAPI" in tech_stack
        assert "Next.js" in tech_stack
        assert "PostgreSQL" in tech_stack
    
    def test_custom_stack(self):
        """Test tech stack with custom configuration."""
        custom_stack = {
            "Frontend": "Vue.js",
            "Backend": "Django",
        }
        features = {}
        tech_stack = _generate_tech_stack(custom_stack, features)
        
        assert "Vue.js" in tech_stack
        assert "Django" in tech_stack
    
    def test_includes_celery_when_enabled(self):
        """Test tech stack includes Celery when background jobs enabled."""
        features = {"needs_background_jobs": True}
        tech_stack = _generate_tech_stack(None, features)
        
        assert "Celery" in tech_stack


class TestGenerateTestingGuide:
    """Tests for testing guide section."""
    
    def test_includes_backend_tests(self):
        """Test testing guide includes backend testing."""
        testing = _generate_testing_guide()
        
        assert "pytest" in testing.lower() or "test" in testing.lower()
    
    def test_includes_frontend_tests(self):
        """Test testing guide includes frontend testing."""
        testing = _generate_testing_guide()
        
        assert "npm test" in testing or "frontend" in testing.lower()
    
    def test_includes_curl_examples(self):
        """Test testing guide includes cURL examples."""
        testing = _generate_testing_guide()
        
        assert "curl" in testing.lower()


class TestGenerateContributing:
    """Tests for contributing section."""
    
    def test_includes_fork_instructions(self):
        """Test contributing includes fork instructions."""
        contributing = _generate_contributing()
        
        assert "Fork" in contributing or "fork" in contributing
    
    def test_includes_pr_instructions(self):
        """Test contributing includes PR instructions."""
        contributing = _generate_contributing()
        
        assert "Pull Request" in contributing or "PR" in contributing
    
    def test_includes_code_style(self):
        """Test contributing includes code style guidelines."""
        contributing = _generate_contributing()
        
        assert "style" in contributing.lower() or "format" in contributing.lower()


class TestGenerateFooter:
    """Tests for footer section."""
    
    def test_includes_license(self):
        """Test footer includes license information."""
        footer = _generate_footer()
        
        assert "License" in footer or "MIT" in footer
    
    def test_includes_current_year(self):
        """Test footer includes current year."""
        footer = _generate_footer()
        current_year = str(datetime.now().year)
        
        assert current_year in footer


class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    def test_empty_entity(self):
        """Test handling empty entity configuration."""
        entity = {}
        features = {}
        
        # Should not raise
        readme = generate_enhanced_readme(
            app_name="Test",
            description="Test",
            entity=entity,
            features=features,
        )
        
        assert isinstance(readme, str)
    
    def test_entity_with_tuple_fields(self):
        """Test handling entity with tuple-style fields."""
        entity = {
            "name": "Item",
            "lower": "item",
            "fields": [
                ("name", "title", "str", True),
                ("desc", "description", "str", False),
            ]
        }
        features = {}
        
        api_docs = _generate_api_docs(entity)
        assert isinstance(api_docs, str)
    
    def test_special_characters_in_name(self):
        """Test handling special characters in app name."""
        entity = {"name": "Item", "lower": "item", "fields": []}
        features = {}
        
        readme = generate_enhanced_readme(
            app_name="My App (v2.0) - Beta!",
            description="Description with 'quotes' and \"double quotes\"",
            entity=entity,
            features=features,
        )
        
        assert "My App" in readme
    
    def test_very_long_description(self):
        """Test handling very long description."""
        entity = {"name": "Item", "lower": "item", "fields": []}
        features = {}
        long_description = "A" * 5000  # Very long description
        
        readme = generate_enhanced_readme(
            app_name="Test App",
            description=long_description,
            entity=entity,
            features=features,
        )
        
        assert long_description[:100] in readme
