"""
Idea Generation Engine for creating startup ideas from intelligence data.
"""

from typing import List
from uuid import uuid4

from loguru import logger

from ..config import PipelineConfig
from ..models import (
    BuyerPersona,
    IdeaCatalog,
    IntelligenceData,
    PainPoint,
    PricingHypothesis,
    RevenueModel,
    StartupIdea,
)


class IdeaGenerationEngine:
    """Engine for generating startup ideas from market intelligence."""

    def __init__(self, config: PipelineConfig):
        """Initialize the idea generation engine."""
        self.config = config
        self.min_ideas = (
            config.idea_generation.min_ideas if config.idea_generation else 50
        )
        self.filters = (
            config.idea_generation.filters if config.idea_generation else {}
        )

    async def generate(self, intelligence: IntelligenceData) -> IdeaCatalog:
        """Generate startup ideas from intelligence data."""
        logger.info("Starting idea generation")

        ideas = []

        # Phase 1: Pain Point Inversion
        ideas.extend(self._pain_point_inversion(intelligence.pain_points))

        # Phase 2: Industry Opportunities
        ideas.extend(self._industry_opportunities(intelligence))

        # Phase 3: Automation Injection
        ideas.extend(self._automation_injection(intelligence.pain_points))

        # Phase 4: Combination Ideas
        ideas.extend(self._combination_ideas(intelligence.pain_points))

        # Apply filters
        ideas = self._apply_filters(ideas)

        # Ensure minimum ideas (with retry limit to prevent infinite loop)
        max_retries = 3
        retry_count = 0
        while len(ideas) < self.min_ideas and retry_count < max_retries:
            logger.warning(
                f"Only {len(ideas)} ideas generated, target is {self.min_ideas} (retry {retry_count + 1}/{max_retries})"
            )
            # Generate more variations
            if ideas:  # Only if we have ideas to vary
                extra_ideas = self._generate_variations(ideas[:5])
                ideas.extend(extra_ideas)
                ideas = self._apply_filters(ideas)
            retry_count += 1

        # Accept partial results if we couldn't reach target
        if len(ideas) < self.min_ideas:
            logger.info(f"Accepting {len(ideas)} ideas (target was {self.min_ideas})")

        logger.info(f"Generated {len(ideas)} startup ideas")

        return IdeaCatalog(ideas=ideas)

    def _pain_point_inversion(self, pain_points: List[PainPoint]) -> List[StartupIdea]:
        """Generate ideas by inverting pain points into solutions."""
        ideas = []

        # Take top pain points by frequency and urgency
        sorted_points = sorted(
            pain_points,
            key=lambda p: p.frequency_count * p.urgency_score,
            reverse=True,
        )

        for pain_point in sorted_points[:30]:
            try:
                # Generate solution name
                keywords = pain_point.keywords[:2] if pain_point.keywords else ["Tool"]
                name = f"{keywords[0].title()} Solution"

                # Create value proposition
                value_prop = self._create_value_proposition(pain_point)

                # Determine revenue model
                revenue_model = self._determine_revenue_model(pain_point)

                # Create buyer persona
                persona = self._create_buyer_persona(pain_point)

                # Market sizing (simplified)
                tam, sam, som = self._estimate_market_size(pain_point)

                idea = StartupIdea(
                    id=uuid4(),
                    name=name,
                    one_liner=f"Solve {pain_point.description[:80]}",
                    problem_statement=pain_point.description,
                    solution_description=value_prop,
                    target_buyer_persona=persona,
                    value_proposition=value_prop,
                    revenue_model=revenue_model,
                    pricing_hypothesis=PricingHypothesis(
                        tiers=["Free", "Pro", "Enterprise"],
                        price_range="$29-$299/month",
                    ),
                    tam_estimate=tam,
                    sam_estimate=sam,
                    som_estimate=som,
                    competitive_landscape=[],
                    differentiation_factors=[
                        "AI-powered automation",
                        "Easy integration",
                        "Fast setup",
                    ],
                    automation_opportunities=[
                        "Automated workflow",
                        "Smart recommendations",
                    ],
                    technical_requirements_summary="Modern web stack with AI/ML",
                    source_pain_point_ids=[pain_point.id],
                )

                ideas.append(idea)

            except Exception as e:
                logger.debug(f"Error generating idea from pain point: {e}")
                continue

        return ideas

    def _industry_opportunities(self, intelligence: IntelligenceData) -> List[StartupIdea]:
        """Generate ideas from emerging industry opportunities."""
        ideas = []

        for industry in intelligence.emerging_industries[:10]:
            try:
                # Find related pain points
                related_pain_points = [
                    pp
                    for pp in intelligence.pain_points
                    if industry.industry_name in pp.affected_industries
                ]

                if not related_pain_points:
                    continue

                # Combine top pain points for this industry
                top_pain_points = sorted(
                    related_pain_points, key=lambda p: p.frequency_count, reverse=True
                )[:3]

                name = f"{industry.industry_name.title()} Platform"
                problem = f"Fragmented solutions in {industry.industry_name}"
                solution = (
                    f"Unified platform for {industry.industry_name} "
                    f"that solves {len(top_pain_points)} major pain points"
                )

                persona = BuyerPersona(
                    title=f"{industry.industry_name} Manager",
                    company_size="10-500 employees",
                    industry=industry.industry_name,
                    budget_authority=True,
                    pain_intensity=industry.opportunity_score,
                )

                idea = StartupIdea(
                    id=uuid4(),
                    name=name,
                    one_liner=solution[:100],
                    problem_statement=problem,
                    solution_description=solution,
                    target_buyer_persona=persona,
                    value_proposition=solution,
                    revenue_model=RevenueModel.SUBSCRIPTION,
                    pricing_hypothesis=PricingHypothesis(
                        tiers=["Starter", "Growth", "Enterprise"],
                        price_range="$99-$999/month",
                    ),
                    tam_estimate=f"${int(industry.opportunity_score * 10)}B",
                    sam_estimate=f"${int(industry.opportunity_score * 2)}B",
                    som_estimate=f"${int(industry.opportunity_score * 100)}M",
                    competitive_landscape=[],
                    differentiation_factors=[
                        "Industry-specific features",
                        "All-in-one platform",
                        "Better integration",
                    ],
                    automation_opportunities=industry.technology_stack_trends[:3],
                    technical_requirements_summary="Enterprise SaaS platform",
                    source_pain_point_ids=[pp.id for pp in top_pain_points],
                )

                ideas.append(idea)

            except Exception as e:
                logger.debug(f"Error generating industry idea: {e}")
                continue

        return ideas

    def _automation_injection(self, pain_points: List[PainPoint]) -> List[StartupIdea]:
        """Generate ideas by adding AI/automation to manual processes."""
        ideas = []

        # Find pain points about manual/time-consuming tasks
        manual_pain_points = [
            pp
            for pp in pain_points
            if any(
                word in pp.description.lower()
                for word in ["manual", "time", "repetitive", "automate", "slow"]
            )
        ]

        for pain_point in manual_pain_points[:15]:
            try:
                keywords = pain_point.keywords[:2] if pain_point.keywords else ["Task"]
                name = f"AI-Powered {keywords[0].title()} Automation"

                solution = (
                    f"Automated solution using AI to handle {pain_point.description[:100]}"
                )

                persona = BuyerPersona(
                    title="Operations Manager",
                    company_size="50-1000 employees",
                    industry=pain_point.affected_industries[0]
                    if pain_point.affected_industries
                    else "software",
                    budget_authority=True,
                    pain_intensity=pain_point.urgency_score,
                )

                idea = StartupIdea(
                    id=uuid4(),
                    name=name,
                    one_liner=f"Automate {pain_point.description[:70]}",
                    problem_statement=pain_point.description,
                    solution_description=solution,
                    target_buyer_persona=persona,
                    value_proposition="Save 10+ hours per week with AI automation",
                    revenue_model=RevenueModel.USAGE,
                    pricing_hypothesis=PricingHypothesis(
                        tiers=["Pay-as-you-go", "Pro", "Enterprise"],
                        price_range="$0.10/task or $149-$799/month",
                    ),
                    tam_estimate="$5B",
                    sam_estimate="$1B",
                    som_estimate="$50M",
                    competitive_landscape=[],
                    differentiation_factors=[
                        "Advanced AI models",
                        "Pay-per-use pricing",
                        "No code required",
                    ],
                    automation_opportunities=[
                        "Full task automation",
                        "Smart scheduling",
                        "Predictive insights",
                    ],
                    technical_requirements_summary="AI/ML platform with LLM integration",
                    source_pain_point_ids=[pain_point.id],
                )

                ideas.append(idea)

            except Exception as e:
                logger.debug(f"Error generating automation idea: {e}")
                continue

        return ideas

    def _combination_ideas(self, pain_points: List[PainPoint]) -> List[StartupIdea]:
        """Generate ideas by combining multiple related pain points."""
        ideas = []

        # Group pain points by industry
        industry_groups = {}
        for pp in pain_points:
            for industry in pp.affected_industries:
                if industry not in industry_groups:
                    industry_groups[industry] = []
                industry_groups[industry].append(pp)

        # Generate combination ideas for industries with multiple pain points
        for industry, pps in industry_groups.items():
            if len(pps) < 3:
                continue

            try:
                # Take top 3 pain points
                top_pps = sorted(pps, key=lambda p: p.frequency_count, reverse=True)[:3]

                name = f"{industry.title()} Command Center"
                problem = f"Multiple disconnected tools needed for {industry}"
                solution = f"All-in-one platform that addresses {len(top_pps)} key problems"

                persona = BuyerPersona(
                    title=f"Head of {industry.title()}",
                    company_size="100-5000 employees",
                    industry=industry,
                    budget_authority=True,
                    pain_intensity=sum(pp.urgency_score for pp in top_pps) / len(top_pps),
                )

                idea = StartupIdea(
                    id=uuid4(),
                    name=name,
                    one_liner=solution,
                    problem_statement=problem,
                    solution_description=solution,
                    target_buyer_persona=persona,
                    value_proposition="One platform to replace 5+ tools",
                    revenue_model=RevenueModel.SUBSCRIPTION,
                    pricing_hypothesis=PricingHypothesis(
                        tiers=["Team", "Business", "Enterprise"],
                        price_range="$199-$1999/month",
                    ),
                    tam_estimate="$10B",
                    sam_estimate="$2B",
                    som_estimate="$100M",
                    competitive_landscape=[],
                    differentiation_factors=[
                        "Unified interface",
                        "Native integrations",
                        "Industry-specific workflows",
                    ],
                    automation_opportunities=[
                        "Cross-tool automation",
                        "Unified analytics",
                    ],
                    technical_requirements_summary="Enterprise platform with microservices",
                    source_pain_point_ids=[pp.id for pp in top_pps],
                )

                ideas.append(idea)

            except Exception as e:
                logger.debug(f"Error generating combination idea: {e}")
                continue

        return ideas

    def _generate_variations(self, base_ideas: List[StartupIdea]) -> List[StartupIdea]:
        """Generate variations of existing ideas."""
        variations = []

        for idea in base_ideas:
            # Create a micro-SaaS variation
            micro_idea = StartupIdea(
                id=uuid4(),
                name=f"{idea.name} Lite",
                one_liner=f"Simplified version: {idea.one_liner[:80]}",
                problem_statement=idea.problem_statement,
                solution_description=f"Focused solution for {idea.one_liner[:50]}",
                target_buyer_persona=BuyerPersona(
                    title="Small Business Owner",
                    company_size="1-10 employees",
                    industry=idea.target_buyer_persona.industry,
                    budget_authority=True,
                    pain_intensity=0.7,
                ),
                value_proposition="Simple, affordable solution for small teams",
                revenue_model=RevenueModel.SUBSCRIPTION,
                pricing_hypothesis=PricingHypothesis(
                    tiers=["Solo", "Team"],
                    price_range="$9-$49/month",
                ),
                tam_estimate="$500M",
                sam_estimate="$100M",
                som_estimate="$10M",
                competitive_landscape=[],
                differentiation_factors=["Simple", "Affordable", "Fast setup"],
                automation_opportunities=[],
                technical_requirements_summary="Lightweight SaaS application",
                source_pain_point_ids=idea.source_pain_point_ids,
            )

            variations.append(micro_idea)

        return variations

    def _create_value_proposition(self, pain_point: PainPoint) -> str:
        """Create value proposition from pain point."""
        return f"Solve {pain_point.description[:100]} with automated workflows"

    def _determine_revenue_model(self, pain_point: PainPoint) -> RevenueModel:
        """Determine appropriate revenue model."""
        # Simplified logic
        if "usage" in pain_point.description.lower():
            return RevenueModel.USAGE
        elif "transaction" in pain_point.description.lower():
            return RevenueModel.TRANSACTION
        else:
            return RevenueModel.SUBSCRIPTION

    def _create_buyer_persona(self, pain_point: PainPoint) -> BuyerPersona:
        """Create buyer persona from pain point."""
        industry = (
            pain_point.affected_industries[0]
            if pain_point.affected_industries
            else "software"
        )

        return BuyerPersona(
            title=f"{industry.title()} Manager",
            company_size="10-500 employees",
            industry=industry,
            budget_authority=True,
            pain_intensity=pain_point.urgency_score,
        )

    def _estimate_market_size(self, pain_point: PainPoint) -> tuple:
        """Estimate TAM, SAM, SOM."""
        # Simplified estimation based on urgency and frequency
        base_tam = pain_point.frequency_count * pain_point.urgency_score * 1000000

        tam = f"${int(base_tam / 1000000)}M"
        sam = f"${int(base_tam / 5000000)}M"
        som = f"${int(base_tam / 50000000)}M"

        return tam, sam, som

    def _apply_filters(self, ideas: List[StartupIdea]) -> List[StartupIdea]:
        """Apply configured filters to ideas."""
        filtered = ideas

        # B2B only filter
        if self.filters.get("b2b_only"):
            filtered = [
                idea
                for idea in filtered
                if idea.target_buyer_persona.budget_authority
            ]

        # Prefer recurring revenue
        if self.filters.get("prefer_recurring_revenue"):
            filtered = sorted(
                filtered,
                key=lambda x: x.revenue_model == RevenueModel.SUBSCRIPTION,
                reverse=True,
            )

        # Remove duplicates by name
        seen_names = set()
        unique_ideas = []
        for idea in filtered:
            if idea.name not in seen_names:
                seen_names.add(idea.name)
                unique_ideas.append(idea)

        return unique_ideas
