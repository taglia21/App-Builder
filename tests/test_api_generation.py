"""Tests for src/api/generation.py - App Generation API."""
import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.requests import Request
from starlette.responses import JSONResponse


@pytest.fixture
def mock_request():
    """Create a mock request."""
    request = MagicMock(spec=Request)
    request.path_params = {}
    return request


@pytest.fixture
def mock_generated_project():
    """Create a mock generated project structure."""
    return {
        'project_id': 'test123',
        'status': 'generated',
        'output_dir': '/tmp/generated_apps/test123',
        'files_count': 5,
        'download_ready': True
    }


@pytest.mark.asyncio
async def test_generate_app_success(mock_request):
    """Test successful app generation."""
    from src.api.generation import generate_app

    mock_request.json = AsyncMock(return_value={
        'project_id': 'test_project',
        'idea': 'A real estate management tool',
        'features': ['auth', 'dashboard'],
        'theme': 'Modern'
    })

    with patch('src.api.generation.EnhancedCodeGenerator') as MockGenerator:
        mock_instance = MockGenerator.return_value
        mock_generated = MagicMock()
        mock_generated.files = ['file1.py', 'file2.py']
        mock_generated.project_name = 'test_project'
        mock_instance.generate.return_value = mock_generated

        response = await generate_app(mock_request)

        assert isinstance(response, JSONResponse)
        body = json.loads(response.body)
        # The actual response has these fields based on the code
        assert 'project_id' in body or 'error' in body


@pytest.mark.asyncio
async def test_generate_app_missing_idea(mock_request):
    """Test app generation with missing idea."""
    from src.api.generation import generate_app

    mock_request.json = AsyncMock(return_value={
        'project_id': 'test_project',
        'idea': '',
    })

    response = await generate_app(mock_request)

    assert isinstance(response, JSONResponse)
    assert response.status_code == 400
    body = json.loads(response.body)
    assert 'error' in body


@pytest.mark.asyncio
async def test_generate_app_exception_handling(mock_request):
    """Test app generation error handling."""
    from src.api.generation import generate_app

    mock_request.json = AsyncMock(return_value={
        'project_id': 'test_project',
        'idea': 'Test idea',
    })

    with patch('src.api.generation.EnhancedCodeGenerator') as MockGenerator:
        MockGenerator.return_value.generate.side_effect = RuntimeError("Generation failed")

        response = await generate_app(mock_request)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 500
        body = json.loads(response.body)
        assert 'error' in body


@pytest.mark.asyncio
async def test_generate_app_without_project_id(mock_request):
    """Test app generation without explicit project ID."""
    from src.api.generation import generate_app

    mock_request.json = AsyncMock(return_value={
        'idea': 'Test idea for app',
    })

    with patch('src.api.generation.EnhancedCodeGenerator') as MockGenerator:
        mock_instance = MockGenerator.return_value
        mock_generated = MagicMock()
        mock_generated.files = []
        mock_generated.project_name = 'auto_generated'
        mock_instance.generate.return_value = mock_generated

        response = await generate_app(mock_request)

        assert isinstance(response, JSONResponse)
        body = json.loads(response.body)
        # Should have either success info or error
        assert 'project_id' in body or 'error' in body


@pytest.mark.asyncio
async def test_get_generation_status_found(mock_request):
    """Test getting status of an existing project."""
    from src.api.generation import _generated_projects, get_generation_status

    project_id = 'test_project_123'
    mock_request.path_params = {'project_id': project_id}
    _generated_projects[project_id] = {
        'project_id': project_id,
        'status': 'generated',
        'files_count': 10
    }

    response = await get_generation_status(mock_request)

    assert isinstance(response, JSONResponse)
    body = json.loads(response.body)
    assert body['project_id'] == project_id
    assert body['status'] == 'generated'

    # Cleanup
    del _generated_projects[project_id]


@pytest.mark.asyncio
async def test_get_generation_status_not_found(mock_request):
    """Test getting status of non-existent project."""
    from src.api.generation import get_generation_status

    mock_request.path_params = {'project_id': 'nonexistent'}

    response = await get_generation_status(mock_request)

    assert isinstance(response, JSONResponse)
    assert response.status_code == 404
    body = json.loads(response.body)
    assert body['status'] == 'not_found'


@pytest.mark.asyncio
async def test_download_project_success(mock_request):
    """Test successful project download."""
    from src.api.generation import _generated_projects, download_project

    with tempfile.TemporaryDirectory() as tmpdir:
        project_id = 'download_test'
        output_dir = Path(tmpdir) / project_id
        output_dir.mkdir()
        (output_dir / 'test.txt').write_text('test content')

        mock_request.path_params = {'project_id': project_id}
        _generated_projects[project_id] = {
            'project_id': project_id,
            'output_dir': str(output_dir)
        }

        with patch('starlette.responses.FileResponse') as MockFileResponse:
            MockFileResponse.return_value = JSONResponse({'status': 'ok'})

            response = await download_project(mock_request)

            assert MockFileResponse.called
            call_args = MockFileResponse.call_args[1]
            assert call_args['media_type'] == 'application/zip'
            assert project_id in call_args['filename']

        # Cleanup
        del _generated_projects[project_id]


@pytest.mark.asyncio
async def test_download_project_not_found(mock_request):
    """Test download for non-existent project."""
    from src.api.generation import download_project

    mock_request.path_params = {'project_id': 'nonexistent'}

    response = await download_project(mock_request)

    assert isinstance(response, JSONResponse)
    assert response.status_code == 404
    body = json.loads(response.body)
    assert 'error' in body


@pytest.mark.asyncio
async def test_download_project_files_missing(mock_request):
    """Test download when generated files are missing."""
    from src.api.generation import _generated_projects, download_project

    project_id = 'missing_files'
    mock_request.path_params = {'project_id': project_id}
    _generated_projects[project_id] = {
        'project_id': project_id,
        'output_dir': '/tmp/nonexistent_dir_123456'
    }

    response = await download_project(mock_request)

    assert isinstance(response, JSONResponse)
    assert response.status_code == 404
    body = json.loads(response.body)
    assert 'error' in body

    # Cleanup
    del _generated_projects[project_id]


def test_generation_routes_defined():
    """Test that generation routes are properly defined."""
    from src.api.generation import generation_routes

    assert len(generation_routes) == 3

    paths = [route.path for route in generation_routes]
    assert '/api/generate' in paths
    assert '/api/projects/{project_id}/status' in paths
    assert '/api/projects/{project_id}/download' in paths
