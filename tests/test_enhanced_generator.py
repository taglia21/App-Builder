"""
Unit tests for Enhanced Idea Generator.

Tests cover:
- MarketResearch dataclass
- EnhancedIdeaGenerator initialization
- Constants and module-level data
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from src.idea_generation.enhanced_generator import (
    MarketResearch,
    TRENDING_CATEGORIES,
    HOT_VERTICALS,
    COMPETITOR_GAPS,
)


class TestMarketResearch:
    """Tests for MarketResearch dataclass."""
    
    def test_initialization(self):
        """Test MarketResearch with all required values."""
        research = MarketResearch(
            trending_technologies=["AI", "Web3"],
            hot_verticals=["Fintech", "Healthtech"],
            funding_trends={"AI": 45.0},
            buyer_preferences={"self_serve": True},
            competitive_gaps=["No good X for Y"]
        )
        
        assert len(research.trending_technologies) == 2
        assert "AI" in research.trending_technologies
        assert len(research.hot_verticals) == 2
        assert research.funding_trends["AI"] == 45.0
    
    def test_dataclass_fields(self):
        """Test MarketResearch dataclass has expected fields."""
        research = MarketResearch(
            trending_technologies=["Tech1"],
            hot_verticals=["Vertical1"],
            funding_trends={"sector": 10.0},
            buyer_preferences={},
            competitive_gaps=["gap1"]
        )
        
        assert hasattr(research, 'trending_technologies')
        assert hasattr(research, 'hot_verticals')
        assert hasattr(research, 'funding_trends')
        assert hasattr(research, 'buyer_preferences')
        assert hasattr(research, 'competitive_gaps')


class TestConstants:
    """Tests for module constants."""
    
    def test_trending_categories_not_empty(self):
        """Test TRENDING_CATEGORIES is populated."""
        assert len(TRENDING_CATEGORIES) > 0
    
    def test_hot_verticals_not_empty(self):
        """Test HOT_VERTICALS is populated."""
        assert len(HOT_VERTICALS) > 0
    
    def test_competitor_gaps_not_empty(self):
        """Test COMPETITOR_GAPS is populated."""
        assert len(COMPETITOR_GAPS) > 0
    
    def test_trending_categories_are_strings(self):
        """Test all trending categories are strings."""
        for category in TRENDING_CATEGORIES:
            assert isinstance(category, str)
    
    def test_hot_verticals_are_strings(self):
        """Test all hot verticals are strings."""
        for vertical in HOT_VERTICALS:
            assert isinstance(vertical, str)
    
    def test_competitor_gaps_are_strings(self):
        """Test all competitor gaps are strings."""
        for gap in COMPETITOR_GAPS:
            assert isinstance(gap, str)
    
    def test_expected_trending_categories(self):
        """Test expected categories are present."""
        assert "AI/ML Automation" in TRENDING_CATEGORIES
        assert "Developer Tools" in TRENDING_CATEGORIES
    
    def test_expected_hot_verticals(self):
        """Test expected verticals are present."""
        assert "FinTech" in HOT_VERTICALS
        assert "HealthTech" in HOT_VERTICALS
    
    def test_expected_competitor_gaps(self):
        """Test expected gaps are present."""
        assert "Complex pricing" in COMPETITOR_GAPS
        assert "Poor onboarding" in COMPETITOR_GAPS


class TestMarketResearchUsage:
    """Tests for MarketResearch usage patterns."""
    
    def test_market_research_with_empty_lists(self):
        """Test MarketResearch with empty lists."""
        research = MarketResearch(
            trending_technologies=[],
            hot_verticals=[],
            funding_trends={},
            buyer_preferences={},
            competitive_gaps=[]
        )
        
        assert research.trending_technologies == []
        assert len(research.hot_verticals) == 0
    
    def test_market_research_iteration(self):
        """Test iterating over MarketResearch fields."""
        research = MarketResearch(
            trending_technologies=["AI", "ML", "Cloud"],
            hot_verticals=["Fintech"],
            funding_trends={"AI": 50.0},
            buyer_preferences={"free_trial": True},
            competitive_gaps=["gap1"]
        )
        
        # Can iterate over technologies
        tech_list = list(research.trending_technologies)
        assert len(tech_list) == 3
    
    def test_market_research_funding_access(self):
        """Test accessing funding trends."""
        research = MarketResearch(
            trending_technologies=[],
            hot_verticals=[],
            funding_trends={"AI": 45.0, "Security": 30.0},
            buyer_preferences={},
            competitive_gaps=[]
        )
        
        assert research.funding_trends.get("AI") == 45.0
        assert research.funding_trends.get("Nonexistent") is None


class TestConstantContent:
    """Tests for constant content validity."""
    
    def test_trending_categories_unique(self):
        """Test all trending categories are unique."""
        assert len(TRENDING_CATEGORIES) == len(set(TRENDING_CATEGORIES))
    
    def test_hot_verticals_unique(self):
        """Test all hot verticals are unique."""
        assert len(HOT_VERTICALS) == len(set(HOT_VERTICALS))
    
    def test_competitor_gaps_unique(self):
        """Test all competitor gaps are unique."""
        assert len(COMPETITOR_GAPS) == len(set(COMPETITOR_GAPS))
    
    def test_categories_have_reasonable_count(self):
        """Test reasonable number of categories."""
        assert len(TRENDING_CATEGORIES) >= 5
        assert len(TRENDING_CATEGORIES) <= 50
    
    def test_verticals_have_reasonable_count(self):
        """Test reasonable number of verticals."""
        assert len(HOT_VERTICALS) >= 5
        assert len(HOT_VERTICALS) <= 50
    
    def test_gaps_have_reasonable_count(self):
        """Test reasonable number of gaps."""
        assert len(COMPETITOR_GAPS) >= 5
        assert len(COMPETITOR_GAPS) <= 50


class TestModuleImports:
    """Tests for module-level imports and availability."""
    
    def test_can_import_market_research(self):
        """Test MarketResearch can be imported."""
        from src.idea_generation.enhanced_generator import MarketResearch
        assert MarketResearch is not None
    
    def test_can_import_constants(self):
        """Test constants can be imported."""
        from src.idea_generation.enhanced_generator import (
            TRENDING_CATEGORIES,
            HOT_VERTICALS,
            COMPETITOR_GAPS,
        )
        assert all([
            TRENDING_CATEGORIES is not None,
            HOT_VERTICALS is not None,
            COMPETITOR_GAPS is not None,
        ])
    
    def test_can_import_enhanced_generator(self):
        """Test EnhancedIdeaGenerator can be imported."""
        from src.idea_generation.enhanced_generator import EnhancedIdeaGenerator
        assert EnhancedIdeaGenerator is not None


class TestMarketResearchEdgeCases:
    """Tests for MarketResearch edge cases."""
    
    def test_large_technology_list(self):
        """Test with large technology list."""
        techs = [f"Tech_{i}" for i in range(100)]
        research = MarketResearch(
            trending_technologies=techs,
            hot_verticals=["V1"],
            funding_trends={},
            buyer_preferences={},
            competitive_gaps=[]
        )
        
        assert len(research.trending_technologies) == 100
    
    def test_special_characters_in_values(self):
        """Test with special characters."""
        research = MarketResearch(
            trending_technologies=["AI/ML", "Low-Code/No-Code"],
            hot_verticals=["FinTech (Banking)"],
            funding_trends={"AI/ML": 50.0},
            buyer_preferences={},
            competitive_gaps=["Poor UI/UX"]
        )
        
        assert "AI/ML" in research.trending_technologies
    
    def test_unicode_values(self):
        """Test with unicode values."""
        research = MarketResearch(
            trending_technologies=["日本語テック"],
            hot_verticals=["中文科技"],
            funding_trends={},
            buyer_preferences={},
            competitive_gaps=[]
        )
        
        assert len(research.trending_technologies) == 1


class TestConstantsForIdeas:
    """Tests for constants used in idea generation."""
    
    def test_categories_cover_ai(self):
        """Test AI/ML category is present."""
        ai_categories = [c for c in TRENDING_CATEGORIES if 'AI' in c or 'ML' in c]
        assert len(ai_categories) >= 1
    
    def test_verticals_cover_finance(self):
        """Test finance vertical is present."""
        finance_verticals = [v for v in HOT_VERTICALS if 'Fin' in v]
        assert len(finance_verticals) >= 1
    
    def test_gaps_cover_ux(self):
        """Test UX-related gaps are present."""
        ux_gaps = [g for g in COMPETITOR_GAPS if 'UI' in g or 'UX' in g]
        assert len(ux_gaps) >= 1


