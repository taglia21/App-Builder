"""LLM-powered idea generation engine."""

import os
import json
import logging
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime

from src.models import StartupIdea, IntelligenceData, IdeaCatalog
from src.llm import get_llm_client

logger = logging.getLogger(__name__)

# Import prompts
try:
    from src.idea_generation.prompts import (
        IDEA_GENERATION_SYSTEM_PROMPT,
        IDEA_GENERATION_USER_PROMPT,
        PAIN_POINT_SUMMARY_TEMPLATE
    )
except ImportError:
    IDEA_GENERATION_SYSTEM_PROMPT = "You are a startup ideation expert."
    IDEA_GENERATION_USER_PROMPT = "Generate {num_ideas} startup ideas based on: {pain_points_summary}"
    PAIN_POINT_SUMMARY_TEMPLATE = "- {description}"


class LLMIdeaGenerationEngine:
    """Generates startup ideas using LLM with enhanced prompts."""
    
    def __init__(self, config, llm_provider: str = 'groq'):
        self.config = config
        self.llm = get_llm_client(llm_provider)
        self.num_ideas = getattr(config.idea_generation, 'min_ideas', 10) if hasattr(config, 'idea_generation') else 10
        self.max_retries = 3
        
        # Import fallback engine (template-based)
        from src.idea_generation.engine import IdeaGenerationEngine
        self.fallback_engine = IdeaGenerationEngine(config)
    
    def _summarize_pain_points(self, pain_points: List[Any], max_points: int = 20) -> str:
        """Create a summary of pain points for the prompt."""
        summaries = []
        for i, pp in enumerate(pain_points[:max_points], 1):
            if hasattr(pp, 'description'):
                summary = PAIN_POINT_SUMMARY_TEMPLATE.format(
                    index=i,
                    source_type=getattr(pp, 'source_type', 'unknown'),
                    description=pp.description[:200],
                    urgency_score=getattr(pp, 'urgency_score', 0.5),
                    industries=', '.join(getattr(pp, 'affected_industries', ['general'])[:3]),
                    keywords=', '.join(getattr(pp, 'keywords', [])[:5])
                )
            else:
                summary = f"### Pain Point {i}\n- {str(pp)[:200]}"
            summaries.append(summary)
        return '\n'.join(summaries)
    
    def _parse_llm_response(self, response: str) -> List[Dict]:
        """Parse LLM response into idea dictionaries."""
        # Try to extract JSON from response
        try:
            # Look for JSON array in response
            start = response.find('[')
            end = response.rfind(']') + 1
            if start != -1 and end > start:
                json_str = response[start:end]
                return json.loads(json_str)
        except json.JSONDecodeError:
            pass
        
        # Try to find JSON objects
        try:
            start = response.find('{')
            end = response.rfind('}') + 1
            if start != -1 and end > start:
                # Might be multiple objects
                json_str = '[' + response[start:end].replace('}\n{', '},{') + ']'
                return json.loads(json_str)
        except json.JSONDecodeError:
            pass
        
        logger.warning("Could not parse LLM response as JSON, using fallback")
        return []
    
    def _dict_to_startup_idea(self, data: Dict, index: int) -> StartupIdea:
        """Convert dictionary to StartupIdea model."""
        from uuid import uuid4
        from src.models import BuyerPersona, PricingHypothesis, RevenueModel
        
        # Extract target customer string and parse it
        target_customer_str = data.get('target_customer', data.get('Target Customer', ''))
        
        # Create BuyerPersona from string or dict
        if isinstance(target_customer_str, dict):
            buyer_persona = BuyerPersona(**target_customer_str)
        else:
            buyer_persona = BuyerPersona(
                title=target_customer_str or f"Unknown {index}",
                company_size="10-500 employees",
                industry=data.get('problem', '')[:50] or "Technology",
                budget_authority=True,
                pain_intensity=0.7
            )
        
        # Parse revenue model
        revenue_str = data.get('revenue_model', data.get('Revenue Model', 'subscription')).lower()
        if 'subscription' in revenue_str:
            revenue_model = RevenueModel.SUBSCRIPTION
        elif 'usage' in revenue_str:
            revenue_model = RevenueModel.USAGE
        elif 'transaction' in revenue_str:
            revenue_model = RevenueModel.TRANSACTION
        else:
            revenue_model = RevenueModel.HYBRID
        
        # Create pricing hypothesis
        pricing = PricingHypothesis(
            tiers=['Basic', 'Pro', 'Enterprise'],
            price_range='$29-$299/month'
        )
        
        return StartupIdea(
            id=uuid4(),
            name=data.get('name', data.get('Name', f'Idea {index}'))[:100],
            one_liner=data.get('one_liner', data.get('One-liner', ''))[:100],
            problem_statement=data.get('problem', data.get('Problem', ''))[:500],
            solution_description=data.get('solution', data.get('Solution', ''))[:500],
            target_buyer_persona=buyer_persona,
            value_proposition=data.get('unique_angle', data.get('Unique Angle', ''))[:300],
            revenue_model=revenue_model,
            pricing_hypothesis=pricing,
            tam_estimate=data.get('tam_estimate', data.get('TAM Estimate', '$1B'))[:50],
            sam_estimate='$500M',
            som_estimate='$50M',
            competitive_landscape=[],
            differentiation_factors=[data.get('moat', data.get('Moat', 'First mover advantage'))],
            automation_opportunities=[],
            technical_requirements_summary=data.get('tech_stack', 'Modern web stack')[:200]
        )
    
    async def generate_async(self, intelligence: IntelligenceData) -> IdeaCatalog:
        """Generate ideas using LLM (async version)."""
        logger.info(f"Generating {self.num_ideas} ideas using LLM...")
        
        # Prepare the prompt
        pain_points_summary = self._summarize_pain_points(intelligence.pain_points)
        
        user_prompt = IDEA_GENERATION_USER_PROMPT.format(
            pain_points_summary=pain_points_summary,
            num_ideas=self.num_ideas
        )
        
        ideas = []
        
        for attempt in range(self.max_retries):
            try:
                # Call LLM (synchronous method in async context)
                response = self.llm.complete(
                    prompt=user_prompt,
                    system_prompt=IDEA_GENERATION_SYSTEM_PROMPT,
                    max_tokens=4000,
                    temperature=0.8,
                    json_mode=False
                )
                
                # Parse response - response is LLMResponse object with .content
                idea_dicts = self._parse_llm_response(response.content)
                
                if idea_dicts:
                    for i, idea_dict in enumerate(idea_dicts):
                        try:
                            idea = self._dict_to_startup_idea(idea_dict, i)
                            ideas.append(idea)
                        except Exception as e:
                            logger.warning(f"Failed to parse idea {i}: {e}")
                    
                    logger.info(f"Generated {len(ideas)} ideas from LLM")
                    break
                else:
                    logger.warning(f"No ideas parsed on attempt {attempt + 1}")
                    
            except Exception as e:
                logger.error(f"LLM generation failed on attempt {attempt + 1}: {e}")
                await asyncio.sleep(2)
        
        # If LLM failed, fall back to template generation
        if not ideas:
            logger.warning("LLM generation failed, falling back to template engine")
            return await self.fallback_engine.generate(intelligence)
        
        return IdeaCatalog(ideas=ideas)
    
    def generate(self, intelligence: IntelligenceData) -> IdeaCatalog:
        """Generate ideas (sync wrapper)."""
        return asyncio.run(self.generate_async(intelligence))
