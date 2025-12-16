"""
Tests for the Idea Generation Engine.
"""

import pytest
from uuid import uuid4

from src.idea_generation.engine import IdeaGenerationEngine
from src.config import PipelineConfig
from src.models import IntelligenceData, PainPoint, SourceType


@pytest.fixture
def mock_config():
    """Create a mock configuration."""
    config = PipelineConfig()
    config.idea_generation = type('obj', (object,), {
        'min_ideas': 10,
        'filters': {'b2b_only': True}
    })()
    return config


@pytest.fixture
def sample_intelligence():
    """Create sample intelligence data."""
    pain_points = [
        PainPoint(
            id=uuid4(),
            description="Manual data entry is time consuming",
            source_type=SourceType.REDDIT,
            source_url="https://reddit.com/example",
            frequency_count=50,
            urgency_score=0.8,
            sentiment_score=-0.6,
            affected_industries=["software"],
            keywords=["manual", "data", "entry"],
            raw_excerpts=["I hate manual data entry"],
        )
    ]
    
    return IntelligenceData(pain_points=pain_points)


@pytest.mark.asyncio
async def test_idea_generation(mock_config, sample_intelligence):
    """Test idea generation from intelligence."""
    engine = IdeaGenerationEngine(mock_config)
    
    ideas = await engine.generate(sample_intelligence)
    
    assert ideas is not None
    assert len(ideas.ideas) >= mock_config.idea_generation.min_ideas
    
    # Check idea structure
    idea = ideas.ideas[0]
    assert idea.name
    assert idea.problem_statement
    assert idea.solution_description
