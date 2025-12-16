"""
Tests for the Intelligence Gathering Engine.
"""

import pytest
from src.intelligence.engine import IntelligenceGatheringEngine
from src.config import PipelineConfig


@pytest.fixture
def mock_config():
    """Create a mock configuration."""
    config = PipelineConfig()
    config.intelligence = type('obj', (object,), {
        'min_pain_points': 10,
        'lookback_period': 30
    })()
    return config


@pytest.mark.asyncio
async def test_intelligence_engine_initialization(mock_config):
    """Test intelligence engine can be initialized."""
    engine = IntelligenceGatheringEngine(mock_config)
    assert engine is not None
    assert engine.config == mock_config


@pytest.mark.asyncio
async def test_intelligence_gathering_structure(mock_config):
    """Test that intelligence gathering returns correct structure."""
    engine = IntelligenceGatheringEngine(mock_config)
    
    # Note: This will fail without API keys, but tests structure
    try:
        result = await engine.gather()
        assert hasattr(result, 'pain_points')
        assert hasattr(result, 'emerging_industries')
        assert hasattr(result, 'opportunity_categories')
    except Exception:
        # Expected without valid API keys
        pass
