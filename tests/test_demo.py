"""Tests for demo mode functionality."""
import pytest
import os
from unittest.mock import Mock, patch, AsyncMock

from src.demo.manager import DemoManager
from src.demo.sample_projects import get_sample_project, SAMPLE_PROJECTS


class TestDemoMode:
    """Test demo mode activation and behavior."""

    @pytest.fixture
    def demo_manager(self):
        """Create a DemoManager instance."""
        return DemoManager()

    def test_demo_mode_detection_enabled(self):
        """Test demo mode is detected when DEMO_MODE=true."""
        with patch.dict(os.environ, {"DEMO_MODE": "true"}):
            manager = DemoManager()
            assert manager.is_demo_mode() is True

    def test_demo_mode_detection_disabled(self):
        """Test demo mode is disabled by default."""
        with patch.dict(os.environ, {}, clear=True):
            manager = DemoManager()
            assert manager.is_demo_mode() is False

    def test_demo_mode_various_values(self):
        """Test demo mode detection with various env var values."""
        test_cases = [
            ("true", True),
            ("True", True),
            ("TRUE", True),
            ("1", True),
            ("false", False),
            ("False", False),
            ("0", False),
            ("", False),
        ]
        
        for value, expected in test_cases:
            with patch.dict(os.environ, {"DEMO_MODE": value}):
                manager = DemoManager()
                assert manager.is_demo_mode() is expected, f"Failed for value: {value}"

    def test_api_keys_not_required_in_demo(self, demo_manager):
        """Test that API keys are not required in demo mode."""
        with patch.dict(os.environ, {"DEMO_MODE": "true"}):
            manager = DemoManager()
            assert manager.requires_api_keys() is False

    def test_api_keys_required_in_production(self, demo_manager):
        """Test that API keys are required outside demo mode."""
        with patch.dict(os.environ, {}, clear=True):
            manager = DemoManager()
            assert manager.requires_api_keys() is True


class TestSampleProjects:
    """Test sample project functionality."""

    def test_sample_projects_exist(self):
        """Test that sample projects are defined."""
        assert len(SAMPLE_PROJECTS) > 0

    def test_get_sample_project_default(self):
        """Test getting the default sample project."""
        project = get_sample_project()
        
        assert project is not None
        assert "name" in project
        assert "description" in project
        assert "files" in project
        assert isinstance(project["files"], dict)

    def test_get_sample_project_by_id(self):
        """Test getting a specific sample project by ID."""
        if SAMPLE_PROJECTS:
            first_id = list(SAMPLE_PROJECTS.keys())[0]
            project = get_sample_project(first_id)
            
            assert project is not None
            assert project["id"] == first_id

    def test_get_nonexistent_sample_project(self):
        """Test getting nonexistent sample project returns None."""
        project = get_sample_project("nonexistent_id_12345")
        assert project is None

    def test_sample_project_structure(self):
        """Test sample project has required structure."""
        project = get_sample_project()
        
        required_fields = ["id", "name", "description", "files", "framework"]
        for field in required_fields:
            assert field in project, f"Missing field: {field}"

    def test_sample_project_files_not_empty(self):
        """Test sample project contains actual files."""
        project = get_sample_project()
        
        assert len(project["files"]) > 0
        assert any(f.endswith(".py") for f in project["files"].keys())

    def test_all_sample_projects_valid(self):
        """Test all sample projects have valid structure."""
        for project_id, project in SAMPLE_PROJECTS.items():
            assert "name" in project
            assert "description" in project
            assert "files" in project
            assert "framework" in project
            assert isinstance(project["files"], dict)


class TestDemoManager:
    """Test DemoManager functionality."""

    @pytest.fixture
    def demo_manager(self):
        """Create a DemoManager instance."""
        return DemoManager()

    @pytest.mark.asyncio
    async def test_load_sample_project(self, demo_manager):
        """Test loading a sample project."""
        with patch.dict(os.environ, {"DEMO_MODE": "true"}):
            manager = DemoManager()
            project = await manager.load_sample_project()
            
            assert project is not None
            assert "files" in project

    @pytest.mark.asyncio
    async def test_load_sample_project_not_in_demo_mode(self, demo_manager):
        """Test loading sample project fails outside demo mode."""
        with patch.dict(os.environ, {}, clear=True):
            manager = DemoManager()
            project = await manager.load_sample_project()
            
            assert project is None

    @pytest.mark.asyncio
    async def test_load_specific_sample_project(self, demo_manager):
        """Test loading a specific sample project by ID."""
        with patch.dict(os.environ, {"DEMO_MODE": "true"}):
            manager = DemoManager()
            
            if SAMPLE_PROJECTS:
                first_id = list(SAMPLE_PROJECTS.keys())[0]
                project = await manager.load_sample_project(first_id)
                
                assert project is not None
                assert project["id"] == first_id

    def test_get_mock_llm_client(self, demo_manager):
        """Test getting mock LLM client in demo mode."""
        with patch.dict(os.environ, {"DEMO_MODE": "true"}):
            manager = DemoManager()
            client = manager.get_llm_client()
            
            assert client is not None
            # Should be mock client
            assert "mock" in client.__class__.__name__.lower()

    @pytest.mark.asyncio
    async def test_mock_llm_response(self, demo_manager):
        """Test mock LLM client returns valid responses in demo mode."""
        with patch.dict(os.environ, {"DEMO_MODE": "true"}):
            manager = DemoManager()
            client = manager.get_llm_client()
            
            response = client.complete("Test prompt")
            
            assert response is not None
            assert hasattr(response, 'content')
            assert len(response.content) > 0

    def test_demo_restrictions(self, demo_manager):
        """Test demo mode restrictions."""
        with patch.dict(os.environ, {"DEMO_MODE": "true"}):
            manager = DemoManager()
            restrictions = manager.get_restrictions()
            
            assert isinstance(restrictions, dict)
            assert "max_projects" in restrictions
            assert "max_file_size" in restrictions

    def test_demo_watermark(self, demo_manager):
        """Test demo mode adds watermark to projects."""
        with patch.dict(os.environ, {"DEMO_MODE": "true"}):
            manager = DemoManager()
            project = {"name": "Test", "files": {}}
            
            watermarked = manager.add_demo_watermark(project)
            
            assert "demo" in str(watermarked).lower() or "sample" in str(watermarked).lower()
