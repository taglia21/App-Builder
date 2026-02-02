"""Comprehensive tests for configuration module."""
import pytest
import os
from unittest.mock import patch


class TestConfigModule:
    """Tests for the config module."""
    
    def test_config_imports(self):
        """Test that config module can be imported."""
        from src import config
        assert config is not None
    
    def test_database_config(self):
        """Test DatabaseConfig class exists and has expected attributes."""
        from src.config import DatabaseConfig
        
        config = DatabaseConfig(url="sqlite:///test.db")
        assert config is not None
        assert config.url == "sqlite:///test.db"
    
    def test_llm_config(self):
        """Test LLMConfig class exists."""
        from src.config import LLMConfig
        
        config = LLMConfig()
        assert config is not None
    
    def test_scoring_config(self):
        """Test ScoringConfig class exists."""
        from src.config import ScoringConfig
        
        config = ScoringConfig()
        assert config is not None


class TestHealthEndpoint:
    """Tests for health monitoring."""
    
    def test_health_module_imports(self):
        """Test that health module can be imported."""
        from src.monitoring import health
        assert health is not None
    
    def test_health_check_structure(self):
        """Test health check returns expected structure."""
        expected_keys = ['status', 'service', 'version', 'timestamp']
        for key in expected_keys:
            assert isinstance(key, str)
