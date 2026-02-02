"""
Main Intelligence-Gathering Engine.
"""

import asyncio
from datetime import timezone, datetime
from typing import Any, Dict, List

from loguru import logger

from ..config import PipelineConfig
from ..models import IntelligenceData
from .base import registry
from .processor import DataProcessor
from .sources import *  # noqa: F403, F401 - Import to register sources


class IntelligenceGatheringEngine:
    """Main engine for gathering and processing market intelligence."""

    def __init__(self, config: PipelineConfig):
        """Initialize the intelligence gathering engine."""
        self.config = config
        self.processor = DataProcessor()
        self.data_sources = []

        # Initialize data sources
        self._initialize_sources()

    def _initialize_sources(self) -> None:
        """Initialize all configured data sources."""
        source_configs = self.config.get_data_sources()

        for source_config in source_configs:
            source_type = source_config.get("type")

            if not source_config.get("enabled", True):
                logger.info(f"Skipping disabled source: {source_type}")
                continue

            try:
                source = registry.create(source_type, source_config)
                self.data_sources.append(source)
                logger.info(f"Initialized data source: {source_type}")
            except Exception as e:
                logger.warning(f"Failed to initialize source {source_type}: {e}")

    async def gather(self, demo_mode: bool = False) -> IntelligenceData:
        """
        Gather intelligence from all sources and process it.
        
        Args:
            demo_mode: If True, use demo data instead of calling APIs
        """
        if demo_mode:
            logger.info("Using demo mode - loading sample data")
            return self._load_demo_data()
        
        logger.info("Starting intelligence gathering process")

        # Gather data from all sources
        raw_data = await self._gather_from_sources()

        logger.info(f"Collected {len(raw_data)} raw data points")

        # Process the data
        intelligence = await self._process_data(raw_data)

        # Validate minimum requirements
        min_pain_points = self.config.intelligence.min_pain_points if self.config.intelligence else 100
        if len(intelligence.pain_points) < min_pain_points:
            logger.warning(
                f"Only {len(intelligence.pain_points)} pain points found, "
                f"minimum is {min_pain_points}"
            )

        logger.info("Intelligence gathering completed")
        logger.info(f"- Pain points: {len(intelligence.pain_points)}")
        logger.info(f"- Emerging industries: {len(intelligence.emerging_industries)}")
        logger.info(f"- Opportunity categories: {len(intelligence.opportunity_categories)}")
        logger.info(f"- Competitor analyses: {len(intelligence.competitor_analysis)}")

        return intelligence

    async def _gather_from_sources(self) -> List[Dict[str, Any]]:
        """Gather data from all sources in parallel."""
        if not self.data_sources:
            logger.warning("No data sources available")
            return []

        # Gather from all sources concurrently
        tasks = [source.gather() for source in self.data_sources]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Combine results
        all_data = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Error gathering from source {i}: {result}")
                continue

            if isinstance(result, list):
                all_data.extend(result)

        return all_data

    async def _process_data(self, raw_data: List[Dict[str, Any]]) -> IntelligenceData:
        """Process raw data into structured intelligence."""
        logger.info("Processing raw data")

        # Extract pain points
        pain_points = self.processor.process_pain_points(raw_data)

        # Extract emerging industries
        emerging_industries = self.processor.extract_emerging_industries(raw_data)

        # Create opportunity categories
        opportunity_categories = self.processor.create_opportunity_categories(
            pain_points, emerging_industries
        )

        # Create competitor analysis (simplified for now)
        competitor_analysis = []

        intelligence = IntelligenceData(
            extraction_timestamp=datetime.now(timezone.utc),
            pain_points=pain_points,
            emerging_industries=emerging_industries,
            opportunity_categories=opportunity_categories,
            competitor_analysis=competitor_analysis,
        )

        return intelligence

    def _load_demo_data(self) -> IntelligenceData:
        """Load demo data for testing without API calls."""
        from uuid import uuid4
        from ..demo_data import (
            get_demo_pain_points,
            get_demo_industries,
            get_demo_competitors,
            get_demo_opportunities
        )
        from ..models import (
            PainPoint, EmergingIndustry, CompetitorAnalysis, 
            OpportunityCategory, SourceType, CompetitionDensity
        )
        
        # Convert dictionaries to Pydantic models
        pain_points = []
        for pp_dict in get_demo_pain_points():
            pp_dict_copy = pp_dict.copy()
            pp_dict_copy['source_type'] = SourceType(pp_dict_copy['source_type'])
            # Replace string ID with UUID
            pp_dict_copy.pop('id')  # Remove string ID, let Pydantic generate UUID
            pain_points.append(PainPoint(**pp_dict_copy))
        
        industries = []
        for ind_dict in get_demo_industries():
            ind_dict_copy = ind_dict.copy()
            ind_dict_copy.pop('id', None)  # Remove string ID if present
            industries.append(EmergingIndustry(**ind_dict_copy))
        
        competitors = []
        for comp_dict in get_demo_competitors():
            competitors.append(CompetitorAnalysis(**comp_dict))
        
        opportunities = []
        for opp_dict in get_demo_opportunities():
            opp_dict_copy = opp_dict.copy()
            opp_dict_copy['competition_density'] = CompetitionDensity(opp_dict_copy['competition_density'])
            # pain_point_ids should be converted from strings to UUIDs
            # For demo, we'll just use empty list since we can't map string IDs to new UUIDs easily
            opp_dict_copy['pain_point_ids'] = []
            opportunities.append(OpportunityCategory(**opp_dict_copy))
        
        logger.info(f"Loaded demo data: {len(pain_points)} pain points, {len(industries)} industries")
        
        return IntelligenceData(
            extraction_timestamp=datetime.now(timezone.utc),
            pain_points=pain_points,
            emerging_industries=industries,
            opportunity_categories=opportunities,
            competitor_analysis=competitors
        )
