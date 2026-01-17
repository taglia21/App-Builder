"""
Generator Snapshot Tests

These tests verify that the code generation engine produces apps with
the expected file structure, including all production-readiness features.

Run with: pytest tests/test_generator.py -v
"""

import pytest
import json
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Set

from src.code_generation.enhanced_engine import EnhancedCodeGenerator
from src.models import ProductPrompt


def create_product_prompt(idea_name: str, description: str = None) -> ProductPrompt:
    """Create a ProductPrompt object for testing."""
    if description is None:
        description = f"{idea_name} - A test application"
    
    prompt_content = json.dumps({
        "product_summary": {
            "solution_overview": description
        }
    })
    
    return ProductPrompt(
        idea_id=uuid.uuid4(),  # Generate valid UUID
        idea_name=idea_name,
        prompt_content=prompt_content
    )


class TestGeneratedAppStructure:
    """Tests for verifying generated app file structure."""
    
    @pytest.fixture
    def generator(self):
        """Create a code generator instance."""
        return EnhancedCodeGenerator()
    
    @pytest.fixture
    def temp_output_dir(self):
        """Create a temporary directory for test output."""
        temp_dir = tempfile.mkdtemp(prefix="test_app_")
        yield temp_dir
        # Cleanup after test
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_generates_backend_core_files(self, generator, temp_output_dir):
        """Test that backend core files are generated."""
        # Generate app
        prompt = create_product_prompt("TestApp", "A simple test application")
        result = generator.generate(
            prompt=prompt,
            output_dir=temp_output_dir,
            theme="Modern"
        )
        
        output_path = Path(temp_output_dir)
        
        # Check core backend files
        expected_files = [
            "backend/app/main.py",
            "backend/app/core/config.py",
            "backend/app/core/auth.py",
            "backend/app/db/session.py",
            "backend/app/db/base_class.py",
            "backend/requirements.txt",
            "backend/Dockerfile",
        ]
        
        for file_path in expected_files:
            assert (output_path / file_path).exists(), f"Missing: {file_path}"
    
    def test_generates_frontend_config_files(self, generator, temp_output_dir):
        """Test that frontend configuration files are generated."""
        prompt = create_product_prompt("TestApp", "A simple test application")
        result = generator.generate(
            prompt=prompt,
            output_dir=temp_output_dir,
            theme="Modern"
        )
        
        output_path = Path(temp_output_dir)
        
        # Check agent-safe config files (Phase C)
        expected_configs = [
            "frontend/src/config/theme.config.ts",
            "frontend/src/config/navigation.config.ts",
            "frontend/src/config/copy.config.ts",
            "frontend/src/config/features.config.ts",
        ]
        
        for file_path in expected_configs:
            assert (output_path / file_path).exists(), f"Missing: {file_path}"
    
    def test_generates_env_files(self, generator, temp_output_dir):
        """Test that environment files are generated with secure defaults."""
        prompt = create_product_prompt("TestApp")
        result = generator.generate(
            prompt=prompt,
            output_dir=temp_output_dir,
            theme="Modern"
        )
        
        output_path = Path(temp_output_dir)
        
        # Check .env.example exists (Phase B)
        env_example = output_path / ".env.example"
        assert env_example.exists(), "Missing .env.example"
        
        # Check .env exists with secure SECRET_KEY (Phase B)
        env_file = output_path / ".env"
        assert env_file.exists(), "Missing .env"
        
        # Verify SECRET_KEY is not a weak default
        env_content = env_file.read_text(encoding="utf-8")
        assert "changeme" not in env_content.lower(), "SECRET_KEY has weak default"
        assert len(env_content) > 100, ".env seems too small"
    
    def test_generates_docker_compose_with_healthchecks(self, generator, temp_output_dir):
        """Test that docker-compose has healthcheck configuration."""
        prompt = create_product_prompt("TestApp")
        result = generator.generate(
            prompt=prompt,
            output_dir=temp_output_dir,
            theme="Modern"
        )
        
        output_path = Path(temp_output_dir)
        compose_file = output_path / "docker-compose.yml"
        
        assert compose_file.exists(), "Missing docker-compose.yml"
        
        content = compose_file.read_text(encoding="utf-8")
        
        # Check for Phase A health features
        assert "healthcheck:" in content, "Missing healthcheck configuration"
        assert "service_healthy" in content, "Missing service_healthy condition"
        assert "pg_isready" in content, "Missing PostgreSQL health check"
    
    def test_generates_health_endpoints(self, generator, temp_output_dir):
        """Test that backend has proper health endpoints."""
        prompt = create_product_prompt("TestApp")
        result = generator.generate(
            prompt=prompt,
            output_dir=temp_output_dir,
            theme="Modern"
        )
        
        output_path = Path(temp_output_dir)
        main_py = output_path / "backend/app/main.py"
        
        assert main_py.exists(), "Missing main.py"
        
        content = main_py.read_text(encoding="utf-8")
        
        # Check for Phase A health endpoints
        assert "/health" in content, "Missing /health endpoint"
        assert "/health/ready" in content, "Missing /health/ready endpoint"
        assert "/health/live" in content, "Missing /health/live endpoint"
        assert "wait_for_db" in content, "Missing wait_for_db call"
    
    def test_generates_db_retry_logic(self, generator, temp_output_dir):
        """Test that database session has retry logic."""
        prompt = create_product_prompt("TestApp")
        result = generator.generate(
            prompt=prompt,
            output_dir=temp_output_dir,
            theme="Modern"
        )
        
        output_path = Path(temp_output_dir)
        session_py = output_path / "backend/app/db/session.py"
        
        assert session_py.exists(), "Missing session.py"
        
        content = session_py.read_text(encoding="utf-8")
        
        # Check for Phase A DB retry features
        assert "wait_for_db" in content, "Missing wait_for_db function"
        assert "exponential" in content.lower() or "max_retries" in content, "Missing retry logic"
        assert "check_db_connection" in content, "Missing check_db_connection function"
    
    def test_generates_secret_key_validation(self, generator, temp_output_dir):
        """Test that config has SECRET_KEY validation."""
        prompt = create_product_prompt("TestApp")
        result = generator.generate(
            prompt=prompt,
            output_dir=temp_output_dir,
            theme="Modern"
        )
        
        output_path = Path(temp_output_dir)
        config_py = output_path / "backend/app/core/config.py"
        
        assert config_py.exists(), "Missing config.py"
        
        content = config_py.read_text(encoding="utf-8")
        
        # Check for Phase B security features
        assert "validate_secret_key" in content, "Missing SECRET_KEY validation"
        assert "WEAK_SECRET_PATTERNS" in content, "Missing weak pattern list"
        assert "_parse_cors_origins" in content, "Missing CORS parsing"
    
    def test_generates_readme_with_quickstart(self, generator, temp_output_dir):
        """Test that README has quick-start documentation."""
        prompt = create_product_prompt("TestApp")
        result = generator.generate(
            prompt=prompt,
            output_dir=temp_output_dir,
            theme="Modern"
        )
        
        output_path = Path(temp_output_dir)
        readme = output_path / "README.md"
        
        assert readme.exists(), "Missing README.md"
        
        content = readme.read_text(encoding="utf-8")
        
        # Check for Phase A documentation
        assert "Quick Start" in content, "Missing Quick Start section"
        assert "docker compose" in content.lower(), "Missing docker compose instructions"
        assert "/health" in content, "Missing health endpoint documentation"
    
    def test_theme_applied_to_globals_css(self, generator, temp_output_dir):
        """Test that selected theme is applied to globals.css."""
        # Test with Cyberpunk theme
        prompt = create_product_prompt("TestApp")
        result = generator.generate(
            prompt=prompt,
            output_dir=temp_output_dir,
            theme="Cyberpunk"
        )
        
        output_path = Path(temp_output_dir)
        globals_css = output_path / "frontend/src/app/globals.css"
        
        assert globals_css.exists(), "Missing globals.css"
        
        content = globals_css.read_text(encoding="utf-8")
        
        # Cyberpunk theme should have distinctive colors
        assert "--background:" in content, "Missing CSS variables"
        # Cyberpunk has purple/neon colors
        assert "260" in content or "320" in content, "Theme colors not applied"
    
    def test_navigation_config_has_entity(self, generator, temp_output_dir):
        """Test that navigation config includes the detected entity."""
        prompt = create_product_prompt("ProjectManager", "Project Management App with tasks")
        result = generator.generate(
            prompt=prompt,
            output_dir=temp_output_dir,
            theme="Modern"
        )
        
        output_path = Path(temp_output_dir)
        nav_config = output_path / "frontend/src/config/navigation.config.ts"
        
        assert nav_config.exists(), "Missing navigation.config.ts"
        
        content = nav_config.read_text(encoding="utf-8")
        
        # Should have Dashboard and dynamic entity
        assert "Dashboard" in content, "Missing Dashboard nav item"
        assert "@ai-safe-edit" in content, "Missing AI safe edit marker"
    

    def test_file_count_reasonable(self, generator, temp_output_dir):
        """Test that generated app has reasonable file count."""
        prompt = create_product_prompt("TestApp")
        result = generator.generate(
            prompt=prompt,
            output_dir=temp_output_dir,
            theme="Modern"
        )
        
        # Count files
        output_path = Path(temp_output_dir)
        file_count = sum(1 for _ in output_path.rglob("*") if _.is_file())
        
        # Should generate 60-100 files for a typical app
        assert file_count >= 60, f"Too few files generated: {file_count}"
        assert file_count <= 150, f"Too many files generated: {file_count}"

    def test_cors_function_defined_before_use(self, generator, temp_output_dir):
        """Regression test: _parse_cors_origins must be defined before Settings class.
        
        This ensures the NameError bug from calling _parse_cors_origins() before
        it was defined cannot recur.
        """
        prompt = create_product_prompt("TestApp")
        result = generator.generate(
            prompt=prompt,
            output_dir=temp_output_dir,
            theme="Modern"
        )
        
        output_path = Path(temp_output_dir)
        config_py = output_path / "backend/app/core/config.py"
        
        assert config_py.exists(), "Missing config.py"
        
        content = config_py.read_text(encoding="utf-8")
        
        # Find positions of function definition and class definition
        func_pos = content.find("def _parse_cors_origins()")
        class_pos = content.find("class Settings(")
        
        assert func_pos != -1, "Missing _parse_cors_origins function definition"
        assert class_pos != -1, "Missing Settings class definition"
        assert func_pos < class_pos, (
            f"_parse_cors_origins (pos={func_pos}) must be defined before "
            f"Settings class (pos={class_pos}) to avoid NameError at import time"
        )

    def test_app_has_required_startup_scripts(self, generator, temp_output_dir):
        """Test that generated app has all required scripts to run out-of-box."""
        prompt = create_product_prompt("TestApp")
        result = generator.generate(
            prompt=prompt,
            output_dir=temp_output_dir,
            theme="Modern"
        )
        
        output_path = Path(temp_output_dir)
        
        # Required files for running the app
        required_files = [
            "docker-compose.yml",
            ".env",
            ".env.example",
            "backend/requirements.txt",
            "backend/Dockerfile",
            "backend/app/main.py",
            "frontend/package.json",
            "frontend/Dockerfile",
        ]
        
        for file_path in required_files:
            assert (output_path / file_path).exists(), f"Missing required startup file: {file_path}"
        
        # Check docker-compose.yml has the required services
        compose_content = (output_path / "docker-compose.yml").read_text(encoding="utf-8")
        assert "backend:" in compose_content, "docker-compose missing backend service"
        assert "frontend:" in compose_content, "docker-compose missing frontend service"
        assert "db:" in compose_content, "docker-compose missing db service"

    def test_schema_files_import_dict(self, generator, temp_output_dir):
        """Regression test: schema files must import Dict to avoid NameError.
        
        This ensures generated schemas can use Dict type hints without crashes.
        """
        prompt = create_product_prompt("TestApp")
        result = generator.generate(
            prompt=prompt,
            output_dir=temp_output_dir,
            theme="Modern"
        )
        
        output_path = Path(temp_output_dir)
        schemas_dir = output_path / "backend/app/schemas"
        
        # Check all schema files have Dict imported
        for schema_file in schemas_dir.glob("*.py"):
            if schema_file.name == "__init__.py":
                continue
            content = schema_file.read_text(encoding="utf-8")
            # If file uses Dict, it must import it
            if "Dict" in content and "Dict]" in content:
                assert "from typing import" in content and "Dict" in content, (
                    f"{schema_file.name} uses Dict but doesn't import it from typing"
                )


class TestGeneratorMetrics:
    """Tests for generator metrics and statistics."""
    
    @pytest.fixture
    def generator(self):
        return EnhancedCodeGenerator()
    
    @pytest.fixture
    def temp_output_dir(self):
        temp_dir = tempfile.mkdtemp(prefix="test_metrics_")
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_returns_codebase_object(self, generator, temp_output_dir):
        """Test that generate() returns a valid GeneratedCodebase object."""
        prompt = create_product_prompt("TestApp")
        result = generator.generate(
            prompt=prompt,
            output_dir=temp_output_dir,
            theme="Modern"
        )
        
        # Check that result has expected attributes
        assert hasattr(result, 'idea_name'), "Missing idea_name attribute"
        assert hasattr(result, 'files_generated'), "Missing files_generated attribute"
    
    def test_metrics_populated(self, generator, temp_output_dir):
        """Test that metrics are properly calculated."""
        prompt = create_product_prompt("TestApp")
        result = generator.generate(
            prompt=prompt,
            output_dir=temp_output_dir,
            theme="Modern"
        )
        
        # Check metrics
        assert result.files_generated > 0, "files_generated not set"
        assert result.lines_of_code > 0, "lines_of_code not set"


