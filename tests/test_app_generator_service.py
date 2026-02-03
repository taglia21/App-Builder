"""Tests for src/app_generator/service.py - App Generator Service."""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.app_generator.service import AppGeneratorService, GenerationProgress


@pytest.fixture
def service():
    """Create an AppGeneratorService instance."""
    return AppGeneratorService()


@pytest.mark.asyncio
async def test_service_initialization(service):
    """Test AppGeneratorService initializes correctly."""
    assert service.template_manager is not None
    assert service.fastapi_manager is not None


@pytest.mark.asyncio
async def test_generate_app_basic_flow(service):
    """Test basic app generation flow."""
    idea = "A task management app"
    app_name = "TaskManager"

    progress_updates = []
    async for progress in service.generate_app(idea, app_name):
        progress_updates.append(progress)
        if progress.step == "complete":
            break

    assert len(progress_updates) > 0
    assert progress_updates[0].step == "analysis"
    assert progress_updates[-1].step == "complete"
    assert progress_updates[-1].progress == 100


@pytest.mark.asyncio
async def test_generate_app_with_features(service):
    """Test app generation with specific features."""
    idea = "E-commerce platform"
    app_name = "ShopApp"
    features = ["auth", "payments", "database"]

    progress_updates = []
    async for progress in service.generate_app(idea, app_name, features=features):
        progress_updates.append(progress)

    assert len(progress_updates) >= 3
    assert any(p.step == "architecture" for p in progress_updates)


@pytest.mark.asyncio
async def test_generate_app_fastapi_framework(service):
    """Test FastAPI app generation."""
    with patch.object(service, '_generate_fastapi_app', new_callable=AsyncMock) as mock_fastapi:
        mock_fastapi.return_value = {
            "main.py": "# FastAPI app",
            "requirements.txt": "fastapi"
        }

        progress_updates = []
        async for progress in service.generate_app("test idea", "TestApp", framework="fastapi"):
            progress_updates.append(progress)

        assert mock_fastapi.called
        assert any(p.step == "generation" for p in progress_updates)


@pytest.mark.asyncio
async def test_generate_app_flask_framework(service):
    """Test Flask app generation."""
    with patch.object(service, '_generate_flask_app', new_callable=AsyncMock) as mock_flask:
        mock_flask.return_value = {
            "app.py": "# Flask app",
            "requirements.txt": "flask"
        }

        progress_updates = []
        async for progress in service.generate_app("test idea", "TestApp", framework="flask"):
            progress_updates.append(progress)

        assert mock_flask.called


@pytest.mark.asyncio
async def test_generate_app_error_handling(service):
    """Test error handling during generation."""
    with patch.object(service, '_generate_architecture', side_effect=RuntimeError("Test error")):
        progress_updates = []
        async for progress in service.generate_app("test", "TestApp"):
            progress_updates.append(progress)

        assert any(p.step == "error" for p in progress_updates)
        error_progress = [p for p in progress_updates if p.step == "error"][0]
        assert error_progress.error is not None


@pytest.mark.asyncio
async def test_generate_architecture_without_anthropic(service):
    """Test architecture generation without Anthropic API."""
    service.anthropic_key = None

    architecture = await service._generate_architecture("Test app", ["auth"])

    assert "models" in architecture
    assert "endpoints" in architecture
    assert "pages" in architecture
    assert architecture["idea"] == "Test app"


@pytest.mark.asyncio
async def test_generate_architecture_with_anthropic(service):
    """Test architecture generation with Anthropic API."""
    service.anthropic_key = "test_key"

    with patch('src.app_generator.service.HAS_ANTHROPIC', True):
        with patch('src.app_generator.service.anthropic.Anthropic') as MockAnthropic:
            mock_client = MagicMock()
            MockAnthropic.return_value = mock_client

            mock_response = MagicMock()
            mock_response.content = [MagicMock(text="Architecture plan")]
            mock_client.messages.create.return_value = mock_response

            architecture = await service._generate_architecture("AI app", [])

            assert "llm_response" in architecture
            assert architecture["llm_response"] == "Architecture plan"


@pytest.mark.asyncio
async def test_generate_architecture_anthropic_error(service):
    """Test architecture generation falls back on Anthropic error."""
    service.anthropic_key = "test_key"

    with patch('src.app_generator.service.HAS_ANTHROPIC', True):
        with patch('src.app_generator.service.anthropic.Anthropic') as MockAnthropic:
            MockAnthropic.side_effect = RuntimeError("API error")

            architecture = await service._generate_architecture("Test", [])

            assert "models" in architecture
            assert "endpoints" in architecture


@pytest.mark.asyncio
async def test_generate_fastapi_app(service):
    """Test FastAPI app file generation."""
    architecture = {
        "models": [{"name": "User", "fields": ["id", "email"]}],
        "endpoints": ["/api/users", "/api/users/{id}"]
    }

    files = await service._generate_fastapi_app("MyApp", architecture, "Test idea")

    assert "main.py" in files
    assert "models.py" in files
    assert "routes.py" in files
    assert "requirements.txt" in files
    assert "Dockerfile" in files
    assert "README.md" in files

    assert "fastapi" in files["requirements.txt"]
    assert "MyApp" in files["README.md"]


@pytest.mark.asyncio
async def test_generate_flask_app(service):
    """Test Flask app file generation."""
    architecture = {
        "models": [{"name": "Product", "fields": ["id", "name", "price"]}]
    }

    files = await service._generate_flask_app("ShopApp", architecture, "E-commerce app")

    assert "app.py" in files
    assert "models.py" in files
    assert "requirements.txt" in files

    assert "flask" in files["requirements.txt"]


@pytest.mark.asyncio
async def test_generate_app_progress_increments(service):
    """Test that progress increments correctly."""
    progress_values = []

    async for progress in service.generate_app("test", "Test"):
        progress_values.append(progress.progress)

    # Progress should generally increase
    assert progress_values[0] < progress_values[-1]
    assert progress_values[-1] == 100


@pytest.mark.asyncio
async def test_generate_app_files_count(service):
    """Test files count tracking during generation."""
    files_counts = []

    async for progress in service.generate_app("test", "Test", framework="fastapi"):
        if progress.step == "generation":
            files_counts.append(progress.files_generated)

    assert len(files_counts) > 0
    assert max(files_counts) == files_counts[-1]


@pytest.mark.asyncio
async def test_generation_progress_validation_step(service):
    """Test validation step is included."""
    steps = []

    async for progress in service.generate_app("test", "Test"):
        steps.append(progress.step)

    assert "validation" in steps


@pytest.mark.asyncio
async def test_service_handles_empty_features(service):
    """Test service handles empty features list."""
    progress_updates = []

    async for progress in service.generate_app("test", "Test", features=None):
        progress_updates.append(progress)

    assert len(progress_updates) > 0
    assert progress_updates[-1].step == "complete"


@pytest.mark.asyncio
async def test_fastapi_manager_called_correctly(service):
    """Test FastAPI manager methods are called."""
    with patch.object(service.fastapi_manager, 'generate_main', return_value="main code"):
        with patch.object(service.fastapi_manager, 'generate_models', return_value="models code"):
            with patch.object(service.fastapi_manager, 'generate_routes', return_value="routes code"):
                files = await service._generate_fastapi_app("App", {"models": [], "endpoints": []}, "idea")

                assert files["main.py"] == "main code"
                assert files["models.py"] == "models code"
                assert files["routes.py"] == "routes code"


@pytest.mark.asyncio
async def test_flask_manager_called_correctly(service):
    """Test Flask template manager methods are called."""
    with patch.object(service.template_manager, 'generate_flask_app', return_value="app code"):
        with patch.object(service.template_manager, 'generate_models', return_value="models code"):
            files = await service._generate_flask_app("App", {"models": []}, "idea")

            assert files["app.py"] == "app code"
            assert files["models.py"] == "models code"
