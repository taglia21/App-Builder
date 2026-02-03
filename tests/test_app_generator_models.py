"""Tests for src/app_generator/models.py - App Generator Data Models."""
import uuid
from datetime import datetime, timezone

import pytest

from src.app_generator.models import (
    AppType,
    Feature,
    GeneratedApp,
    GeneratedFile,
    GenerationProgress,
    GenerationRequest,
    TechStack,
)


def test_app_type_enum():
    """Test AppType enum values."""
    assert AppType.SAAS == "saas"
    assert AppType.MARKETPLACE == "marketplace"
    assert AppType.ECOMMERCE == "ecommerce"
    assert AppType.DASHBOARD == "dashboard"
    assert AppType.SOCIAL == "social"
    assert AppType.PORTFOLIO == "portfolio"
    assert AppType.API == "api"
    assert AppType.OTHER == "other"


def test_tech_stack_enum():
    """Test TechStack enum values."""
    assert TechStack.PYTHON_FASTAPI == "python-fastapi"
    assert TechStack.NEXTJS == "nextjs"
    assert TechStack.DJANGO == "django"
    assert TechStack.FLASK == "flask"
    assert TechStack.EXPRESS == "express"


def test_feature_enum():
    """Test Feature enum values."""
    assert Feature.AUTH == "auth"
    assert Feature.PAYMENTS == "payments"
    assert Feature.DATABASE == "database"
    assert Feature.API == "api"
    assert Feature.EMAIL == "email"
    assert Feature.REALTIME == "realtime"


def test_generation_request_defaults():
    """Test GenerationRequest with default values."""
    req = GenerationRequest(
        project_name="TestApp",
        description="A test application",
        app_type=AppType.SAAS,
        tech_stack=TechStack.PYTHON_FASTAPI,
        features=[Feature.AUTH, Feature.DATABASE],
        user_id="user123"
    )

    assert req.project_name == "TestApp"
    assert req.description == "A test application"
    assert req.app_type == AppType.SAAS
    assert req.tech_stack == TechStack.PYTHON_FASTAPI
    assert Feature.AUTH in req.features
    assert isinstance(req.id, str)
    assert isinstance(req.created_at, datetime)


def test_generation_request_custom_id():
    """Test GenerationRequest with custom ID."""
    custom_id = str(uuid.uuid4())
    req = GenerationRequest(
        project_name="TestApp",
        description="Test",
        app_type=AppType.API,
        tech_stack=TechStack.FLASK,
        features=[],
        user_id="user123",
        id=custom_id
    )

    assert req.id == custom_id


def test_generated_file_creation():
    """Test GeneratedFile creation."""
    file = GeneratedFile(
        path="src/main.py",
        content="print('Hello')",
        language="python"
    )

    assert file.path == "src/main.py"
    assert file.content == "print('Hello')"
    assert file.language == "python"


def test_generated_file_default_language():
    """Test GeneratedFile default language."""
    file = GeneratedFile(
        path="test.txt",
        content="content"
    )

    assert file.language == "python"


def test_generated_file_to_dict():
    """Test GeneratedFile to_dict conversion."""
    file = GeneratedFile(
        path="app.py",
        content="# App code",
        language="python"
    )

    result = file.to_dict()

    assert result["path"] == "app.py"
    assert result["content"] == "# App code"
    assert result["language"] == "python"


def test_generated_app_creation():
    """Test GeneratedApp creation."""
    files = [
        GeneratedFile("main.py", "code1", "python"),
        GeneratedFile("test.py", "code2", "python")
    ]

    app = GeneratedApp(
        id="app123",
        project_name="MyApp",
        files=files,
        tech_stack=TechStack.PYTHON_FASTAPI,
        features=[Feature.AUTH, Feature.API],
        readme="# MyApp\n\nREADME content",
        requirements=["fastapi>=0.100.0", "uvicorn>=0.22.0"],
        env_template="DB_URL=postgresql://localhost/myapp"
    )

    assert app.id == "app123"
    assert app.project_name == "MyApp"
    assert len(app.files) == 2
    assert app.tech_stack == TechStack.PYTHON_FASTAPI
    assert Feature.AUTH in app.features
    assert "MyApp" in app.readme
    assert len(app.requirements) == 2
    assert app.docker_compose is None
    assert app.dockerfile is None


def test_generated_app_with_docker():
    """Test GeneratedApp with Docker configurations."""
    app = GeneratedApp(
        id="app123",
        project_name="MyApp",
        files=[],
        tech_stack=TechStack.NEXTJS,
        features=[],
        readme="README",
        requirements=[],
        env_template="",
        dockerfile="FROM node:18",
        docker_compose="version: '3.8'"
    )

    assert app.dockerfile == "FROM node:18"
    assert app.docker_compose == "version: '3.8'"


def test_generated_app_to_dict():
    """Test GeneratedApp to_dict conversion."""
    files = [GeneratedFile("main.py", "code", "python")]
    app = GeneratedApp(
        id="app123",
        project_name="MyApp",
        files=files,
        tech_stack=TechStack.DJANGO,
        features=[Feature.DATABASE],
        readme="README",
        requirements=["django>=4.0"],
        env_template="SECRET_KEY=xxx",
        dockerfile="FROM python:3.11"
    )

    result = app.to_dict()

    assert result["id"] == "app123"
    assert result["project_name"] == "MyApp"
    assert len(result["files"]) == 1
    assert result["tech_stack"] == "django"
    assert "database" in result["features"]
    assert result["readme"] == "README"
    assert "django>=4.0" in result["requirements"]
    assert result["env_template"] == "SECRET_KEY=xxx"
    assert result["dockerfile"] == "FROM python:3.11"
    assert isinstance(result["created_at"], str)


def test_generation_progress_minimal():
    """Test GenerationProgress with minimal fields."""
    progress = GenerationProgress(
        step="init",
        progress=0,
        message="Starting generation"
    )

    assert progress.step == "init"
    assert progress.progress == 0
    assert progress.message == "Starting generation"
    assert progress.files_generated == 0
    assert progress.total_files == 0


def test_generation_progress_complete():
    """Test GenerationProgress with all fields."""
    progress = GenerationProgress(
        step="generation",
        progress=75,
        message="Generating files",
        files_generated=15,
        total_files=20
    )

    assert progress.step == "generation"
    assert progress.progress == 75
    assert progress.message == "Generating files"
    assert progress.files_generated == 15
    assert progress.total_files == 20


def test_generated_app_created_at_default():
    """Test GeneratedApp has default created_at."""
    before = datetime.now(timezone.utc)

    app = GeneratedApp(
        id="test",
        project_name="Test",
        files=[],
        tech_stack=TechStack.FLASK,
        features=[],
        readme="",
        requirements=[],
        env_template=""
    )

    after = datetime.now(timezone.utc)

    assert before <= app.created_at <= after


def test_generation_request_created_at_default():
    """Test GenerationRequest has default created_at."""
    before = datetime.now(timezone.utc)

    req = GenerationRequest(
        project_name="Test",
        description="Test",
        app_type=AppType.OTHER,
        tech_stack=TechStack.EXPRESS,
        features=[],
        user_id="user123"
    )

    after = datetime.now(timezone.utc)

    assert before <= req.created_at <= after
