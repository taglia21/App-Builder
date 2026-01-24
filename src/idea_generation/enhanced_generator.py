"""
Enhanced Idea Generation with Market Research and Competitor Analysis

Generates more innovative, market-viable SaaS ideas with:
- Real market opportunity validation
- Competitor gap analysis
- Unique positioning strategies
- Revenue model optimization
"""

import random
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4
from dataclasses import dataclass

from loguru import logger

from ..config import PipelineConfig
from ..models import (
    BuyerPersona,
    IntelligenceData,
    PainPoint,
    PricingHypothesis,
    RevenueModel,
    StartupIdea,
)


@dataclass
class MarketResearch:
    """Market research context for idea generation."""
    trending_technologies: List[str]
    hot_verticals: List[str]
    funding_trends: Dict[str, float]  # sector -> growth %
    buyer_preferences: Dict[str, Any]
    competitive_gaps: List[str]


# Trending SaaS categories and technologies (2024-2026)
TRENDING_CATEGORIES = [
    "AI/ML Automation",
    "Developer Tools",
    "Security & Compliance",
    "Revenue Operations",
    "Customer Success",
    "Product-Led Growth",
    "Workflow Automation",
    "Data Integration",
    "Remote Collaboration",
    "API Infrastructure",
    "Low-Code/No-Code",
    "Vertical SaaS",
]

# High-growth verticals
HOT_VERTICALS = [
    "FinTech",
    "HealthTech", 
    "EdTech",
    "PropTech",
    "LegalTech",
    "HRTech",
    "CleanTech",
    "AgriTech",
    "LogiTech",
    "RetailTech",
]

# Product positioning templates
POSITIONING_TEMPLATES = [
    "{verb} for {audience}",
    "The {category} platform that {differentiation}",
    "{audience}'s {solution} that {benefit}",
    "Turn {problem} into {outcome}",
    "The only {category} that {unique_feature}",
]

# Unique value proposition patterns
UVP_PATTERNS = [
    "reduces {metric} by {percentage}%",
    "saves {time_unit} per {activity}",
    "increases {positive_metric} by {multiplier}x",
    "eliminates {pain_point} completely",
    "automates {task} in {time_frame}",
    "connects {system_a} with {system_b} seamlessly",
]

# Competitor weakness patterns to exploit
COMPETITOR_GAPS = [
    "Complex pricing",
    "Poor onboarding",
    "Limited integrations",
    "Slow customer support",
    "Legacy UI/UX",
    "No mobile support",
    "Missing AI features",
    "Vendor lock-in",
    "Expensive for SMBs",
    "Missing workflow automation",
]


class EnhancedIdeaGenerator:
    """
    Enhanced idea generation with market research and positioning.
    
    Generates ideas that are:
    - Aligned with market trends
    - Differentiated from competitors
    - Positioned for specific buyer personas
    - Optimized for revenue potential
    """
    
    def __init__(self, config: PipelineConfig, llm_client=None):
        self.config = config
        self.llm_client = llm_client
        self.min_ideas = config.idea_generation.min_ideas if config.idea_generation else 25
        
    def generate_ideas(
        self, 
        intelligence: IntelligenceData,
        market_research: Optional[MarketResearch] = None
    ) -> List[StartupIdea]:
        """Generate enhanced startup ideas with market context."""
        
        if market_research is None:
            market_research = self._create_default_market_research()
        
        ideas = []
        
        # Strategy 1: Trend-aligned automation
        ideas.extend(self._generate_trend_aligned_ideas(intelligence, market_research))
        
        # Strategy 2: Vertical SaaS opportunities
        ideas.extend(self._generate_vertical_saas_ideas(intelligence, market_research))
        
        # Strategy 3: Competitor gap exploitation
        ideas.extend(self._generate_competitive_gap_ideas(intelligence, market_research))
        
        # Strategy 4: AI-first solutions
        ideas.extend(self._generate_ai_first_ideas(intelligence))
        
        # Strategy 5: Integration/workflow plays
        ideas.extend(self._generate_integration_ideas(intelligence))
        
        # Deduplicate and rank
        ideas = self._deduplicate_ideas(ideas)
        
        # Enhance ideas with better positioning
        ideas = [self._enhance_positioning(idea, market_research) for idea in ideas]
        
        logger.info(f"Generated {len(ideas)} enhanced startup ideas")
        return ideas
    
    def _create_default_market_research(self) -> MarketResearch:
        """Create default market research context."""
        return MarketResearch(
            trending_technologies=TRENDING_CATEGORIES,
            hot_verticals=HOT_VERTICALS,
            funding_trends={
                "AI/ML": 45.0,
                "Security": 32.0,
                "FinTech": 28.0,
                "Developer Tools": 25.0,
                "HealthTech": 22.0,
            },
            buyer_preferences={
                "self_serve": True,
                "free_trial": True,
                "instant_value": True,
                "integrations": ["Slack", "Salesforce", "HubSpot", "Notion"],
            },
            competitive_gaps=COMPETITOR_GAPS,
        )
    
    def _generate_trend_aligned_ideas(
        self, 
        intelligence: IntelligenceData,
        market_research: MarketResearch
    ) -> List[StartupIdea]:
        """Generate ideas aligned with current market trends."""
        ideas = []
        
        # Match pain points to trending categories
        for pain_point in intelligence.pain_points[:15]:
            best_trend = self._match_pain_to_trend(pain_point, market_research)
            if not best_trend:
                continue
            
            # Create trendy product name
            name = self._generate_product_name(pain_point, best_trend)
            
            # Create compelling one-liner
            one_liner = self._generate_one_liner(pain_point, best_trend)
            
            # Identify specific buyer
            persona = self._create_detailed_persona(pain_point)
            
            # Calculate realistic TAM/SAM/SOM
            tam, sam, som = self._calculate_market_size(pain_point, best_trend)
            
            # Identify competitors and differentiation
            competitors = self._identify_competitors(pain_point, best_trend)
            differentiators = self._generate_differentiators(competitors)
            
            idea = StartupIdea(
                id=uuid4(),
                name=name,
                one_liner=one_liner,
                problem_statement=self._enhance_problem_statement(pain_point),
                solution_description=self._generate_solution(pain_point, best_trend),
                target_buyer_persona=persona,
                value_proposition=self._generate_uvp(pain_point),
                revenue_model=self._optimize_revenue_model(pain_point, persona),
                pricing_hypothesis=self._create_pricing_hypothesis(persona),
                tam_estimate=tam,
                sam_estimate=sam,
                som_estimate=som,
                competitive_landscape=competitors,
                differentiation_factors=differentiators,
                automation_opportunities=self._find_automation_opportunities(pain_point),
                technical_requirements_summary=self._generate_tech_requirements(best_trend),
                source_pain_point_ids=[pain_point.id],
            )
            ideas.append(idea)
        
        return ideas
    
    def _generate_vertical_saas_ideas(
        self,
        intelligence: IntelligenceData,
        market_research: MarketResearch
    ) -> List[StartupIdea]:
        """Generate vertical SaaS ideas for specific industries."""
        ideas = []
        
        # Group pain points by industry
        industry_pains: Dict[str, List[PainPoint]] = {}
        for pp in intelligence.pain_points:
            for industry in pp.affected_industries:
                if industry not in industry_pains:
                    industry_pains[industry] = []
                industry_pains[industry].append(pp)
        
        # Focus on hot verticals
        for vertical in market_research.hot_verticals[:5]:
            # Find matching industry
            matching_industry = None
            for industry in industry_pains:
                if vertical.lower().replace("tech", "") in industry.lower():
                    matching_industry = industry
                    break
            
            if not matching_industry:
                # Create synthetic opportunity
                name = f"{vertical} Operations Hub"
                problem = f"Fragmented tools and workflows in {vertical}"
                solution = f"All-in-one platform designed specifically for {vertical} businesses"
            else:
                pains = industry_pains[matching_industry][:3]
                combined_problem = " and ".join([p.description[:50] for p in pains])
                name = f"{vertical} Command Center"
                problem = combined_problem
                solution = f"Purpose-built platform solving {len(pains)} critical {vertical} challenges"
            
            persona = BuyerPersona(
                title=f"{vertical} Operations Director",
                company_size="50-500 employees",
                industry=vertical,
                budget_authority=True,
                pain_intensity=0.85,
            )
            
            idea = StartupIdea(
                id=uuid4(),
                name=name,
                one_liner=f"The operating system for modern {vertical} businesses",
                problem_statement=problem,
                solution_description=solution,
                target_buyer_persona=persona,
                value_proposition=f"Reduce operational complexity by 60% with purpose-built {vertical} tools",
                revenue_model=RevenueModel.SUBSCRIPTION,
                pricing_hypothesis=PricingHypothesis(
                    tiers=["Growth", "Scale", "Enterprise"],
                    price_range="$199-$999/month",
                ),
                tam_estimate="$5B",
                sam_estimate="$800M",
                som_estimate="$50M",
                competitive_landscape=["Generic SaaS tools", "Legacy on-prem", "Point solutions"],
                differentiation_factors=[
                    f"{vertical}-specific workflows",
                    "Industry compliance built-in",
                    "Specialized integrations",
                    "Domain expert onboarding",
                ],
                automation_opportunities=[
                    f"{vertical} reporting automation",
                    "Compliance monitoring",
                    "Customer lifecycle management",
                ],
                technical_requirements_summary=f"Enterprise SaaS with {vertical}-specific features",
                source_pain_point_ids=[],
            )
            ideas.append(idea)
        
        return ideas
    
    def _generate_competitive_gap_ideas(
        self,
        intelligence: IntelligenceData,
        market_research: MarketResearch
    ) -> List[StartupIdea]:
        """Generate ideas that exploit competitor weaknesses."""
        ideas = []
        
        gap_opportunity_pairs = [
            ("Complex pricing", "Simple, transparent pricing", "Clear Pricing SaaS"),
            ("Poor onboarding", "5-minute setup", "Instant Setup Platform"),
            ("Limited integrations", "Universal connector", "Integration Hub"),
            ("Slow customer support", "AI-powered instant support", "Smart Support"),
            ("Legacy UI/UX", "Modern, intuitive interface", "Modern Workspace"),
            ("Missing AI features", "AI-first design", "AI-Powered Tools"),
        ]
        
        for gap, solution, name_suffix in gap_opportunity_pairs[:3]:
            # Find pain points related to this gap
            related_pains = [
                pp for pp in intelligence.pain_points
                if any(word in pp.description.lower() for word in gap.lower().split())
            ]
            
            if related_pains:
                pain = related_pains[0]
                base_name = pain.keywords[0].title() if pain.keywords else "Workflow"
            else:
                base_name = random.choice(["Task", "Project", "Team", "Data"])
            
            name = f"{base_name} {name_suffix}"
            
            idea = StartupIdea(
                id=uuid4(),
                name=name,
                one_liner=f"The {base_name.lower()} tool with {solution}",
                problem_statement=f"Existing solutions suffer from {gap.lower()}",
                solution_description=f"Built from the ground up with {solution} as a core principle",
                target_buyer_persona=BuyerPersona(
                    title="Department Head",
                    company_size="10-200 employees",
                    industry="Technology",
                    budget_authority=True,
                    pain_intensity=0.7,
                ),
                value_proposition=f"Finally, {base_name.lower()} management with {solution}",
                revenue_model=RevenueModel.FREEMIUM,
                pricing_hypothesis=PricingHypothesis(
                    tiers=["Free", "Pro", "Team"],
                    price_range="$0-$49/user/month",
                ),
                tam_estimate="$3B",
                sam_estimate="$500M",
                som_estimate="$25M",
                competitive_landscape=["Legacy incumbents", "Complex enterprise tools"],
                differentiation_factors=[
                    solution,
                    "Product-led growth",
                    "Self-serve onboarding",
                    "Generous free tier",
                ],
                automation_opportunities=["Workflow automation", "Smart defaults"],
                technical_requirements_summary="Modern web app with excellent UX",
                source_pain_point_ids=[],
            )
            ideas.append(idea)
        
        return ideas
    
    def _generate_ai_first_ideas(self, intelligence: IntelligenceData) -> List[StartupIdea]:
        """Generate AI-first solution ideas."""
        ideas = []
        
        ai_opportunity_patterns = [
            ("data entry", "AI Data Entry Agent", "automates data entry with 99% accuracy"),
            ("reporting", "AI Report Generator", "creates reports automatically from your data"),
            ("analysis", "AI Analyst", "provides instant insights from complex data"),
            ("scheduling", "AI Scheduler", "optimizes schedules using machine learning"),
            ("customer", "AI Customer Agent", "handles customer inquiries 24/7 with human-like responses"),
            ("document", "AI Document Processor", "extracts and processes documents automatically"),
            ("email", "AI Email Assistant", "drafts, summarizes, and prioritizes emails"),
            ("code", "AI Code Assistant", "reviews, suggests, and generates code"),
        ]
        
        for keyword, name, benefit in ai_opportunity_patterns:
            # Find matching pain points
            matching = [pp for pp in intelligence.pain_points if keyword in pp.description.lower()]
            
            if matching:
                pain = matching[0]
                problem = pain.description
            else:
                problem = f"Manual {keyword} tasks are time-consuming and error-prone"
            
            idea = StartupIdea(
                id=uuid4(),
                name=name,
                one_liner=f"AI that {benefit}",
                problem_statement=problem,
                solution_description=f"Advanced AI system that {benefit}, saving hours of manual work",
                target_buyer_persona=BuyerPersona(
                    title="Operations Manager",
                    company_size="50-500 employees",
                    industry="Any",
                    budget_authority=True,
                    pain_intensity=0.8,
                ),
                value_proposition=f"Reduce {keyword} time by 90% with AI automation",
                revenue_model=RevenueModel.USAGE_BASED,
                pricing_hypothesis=PricingHypothesis(
                    tiers=["Pay-as-you-go", "Pro", "Enterprise"],
                    price_range="$0.01-$0.10/task or $99-$499/month unlimited",
                ),
                tam_estimate="$10B",
                sam_estimate="$1B",
                som_estimate="$50M",
                competitive_landscape=["Manual processes", "Basic automation"],
                differentiation_factors=[
                    "State-of-the-art AI models",
                    "Continuous learning",
                    "High accuracy",
                    "Easy integration",
                ],
                automation_opportunities=[
                    f"Full {keyword} automation",
                    "Quality assurance automation",
                    "Workflow orchestration",
                ],
                technical_requirements_summary="AI/ML platform with LLM integration",
                source_pain_point_ids=[pain.id for pain in matching[:3]],
            )
            ideas.append(idea)
        
        return ideas[:5]  # Limit to top 5
    
    def _generate_integration_ideas(self, intelligence: IntelligenceData) -> List[StartupIdea]:
        """Generate integration and workflow ideas."""
        ideas = []
        
        # Popular integration pairs
        integration_pairs = [
            ("Slack", "Salesforce", "CRM notifications"),
            ("HubSpot", "Stripe", "Revenue tracking"),
            ("Notion", "Linear", "Project sync"),
            ("GitHub", "Jira", "Dev workflow"),
            ("Zapier", "AI", "Smart automation"),
        ]
        
        for tool_a, tool_b, use_case in integration_pairs[:3]:
            name = f"{tool_a} + {tool_b} Connector"
            
            idea = StartupIdea(
                id=uuid4(),
                name=name,
                one_liner=f"Seamless {use_case} between {tool_a} and {tool_b}",
                problem_statement=f"Disconnected data between {tool_a} and {tool_b} causes workflow friction",
                solution_description=f"Native integration that syncs {tool_a} and {tool_b} in real-time with smart automation",
                target_buyer_persona=BuyerPersona(
                    title="RevOps Manager",
                    company_size="50-500 employees",
                    industry="SaaS",
                    budget_authority=True,
                    pain_intensity=0.75,
                ),
                value_proposition=f"Save 5+ hours/week on {use_case} with automatic sync",
                revenue_model=RevenueModel.SUBSCRIPTION,
                pricing_hypothesis=PricingHypothesis(
                    tiers=["Starter", "Growth", "Scale"],
                    price_range="$49-$299/month",
                ),
                tam_estimate="$2B",
                sam_estimate="$300M",
                som_estimate="$15M",
                competitive_landscape=["Manual exports", "Generic iPaaS", "Custom scripts"],
                differentiation_factors=[
                    f"Purpose-built for {tool_a} + {tool_b}",
                    "Real-time sync",
                    "Smart conflict resolution",
                    "No-code setup",
                ],
                automation_opportunities=["Data sync", "Trigger automation", "Error handling"],
                technical_requirements_summary="API integration platform",
                source_pain_point_ids=[],
            )
            ideas.append(idea)
        
        return ideas
    
    # Helper methods
    def _match_pain_to_trend(self, pain_point: PainPoint, research: MarketResearch) -> Optional[str]:
        """Match a pain point to the best trending category."""
        pain_text = pain_point.description.lower()
        
        trend_keywords = {
            "AI/ML Automation": ["automat", "manual", "repetitive", "ai", "ml"],
            "Developer Tools": ["developer", "code", "debug", "deploy", "api"],
            "Security & Compliance": ["security", "compliance", "audit", "risk"],
            "Revenue Operations": ["revenue", "sales", "pipeline", "forecast"],
            "Customer Success": ["customer", "churn", "retention", "support"],
            "Workflow Automation": ["workflow", "process", "efficiency", "task"],
        }
        
        best_match = None
        best_score = 0
        
        for trend, keywords in trend_keywords.items():
            score = sum(1 for kw in keywords if kw in pain_text)
            if score > best_score:
                best_score = score
                best_match = trend
        
        return best_match if best_score > 0 else random.choice(research.trending_technologies)
    
    def _generate_product_name(self, pain_point: PainPoint, trend: str) -> str:
        """Generate a memorable product name."""
        prefixes = ["Hyper", "Ultra", "Auto", "Smart", "Next", "Meta", "Flow", "Sync"]
        suffixes = ["AI", "Hub", "Stack", "Cloud", "Labs", "io", "ly", "ify"]
        
        if pain_point.keywords:
            base = pain_point.keywords[0].title()
        else:
            base = trend.split()[0]
        
        return f"{random.choice(prefixes)}{base}{random.choice(suffixes)}"
    
    def _generate_one_liner(self, pain_point: PainPoint, trend: str) -> str:
        """Generate a compelling one-liner."""
        templates = [
            f"Automate {pain_point.keywords[0] if pain_point.keywords else 'tasks'} with AI",
            f"The {trend.lower()} platform that saves you hours daily",
            f"Turn {pain_point.description[:30].lower()} into a solved problem",
        ]
        return random.choice(templates)
    
    def _create_detailed_persona(self, pain_point: PainPoint) -> BuyerPersona:
        """Create a detailed buyer persona."""
        titles = [
            "VP of Operations", "Director of Engineering", "Head of Product",
            "Chief Revenue Officer", "IT Director", "Operations Manager"
        ]
        
        return BuyerPersona(
            title=random.choice(titles),
            company_size="50-500 employees",
            industry=pain_point.affected_industries[0] if pain_point.affected_industries else "Technology",
            budget_authority=True,
            pain_intensity=min(pain_point.urgency_score, 1.0),
        )
    
    def _calculate_market_size(self, pain_point: PainPoint, trend: str) -> Tuple[str, str, str]:
        """Calculate realistic TAM/SAM/SOM."""
        base_tam = random.randint(5, 50)
        sam_ratio = random.uniform(0.1, 0.3)
        som_ratio = random.uniform(0.01, 0.05)
        
        return (
            f"${base_tam}B",
            f"${int(base_tam * sam_ratio * 1000)}M",
            f"${int(base_tam * som_ratio * 1000)}M"
        )
    
    def _identify_competitors(self, pain_point: PainPoint, trend: str) -> List[str]:
        """Identify likely competitors."""
        generic_competitors = [
            "Manual processes and spreadsheets",
            "Legacy enterprise software",
            "Point solutions",
            "In-house tools",
        ]
        return generic_competitors[:3]
    
    def _generate_differentiators(self, competitors: List[str]) -> List[str]:
        """Generate differentiation factors."""
        return [
            "AI-powered automation",
            "10x faster implementation",
            "Self-serve onboarding",
            "Usage-based pricing",
            "Best-in-class integrations",
        ][:4]
    
    def _enhance_problem_statement(self, pain_point: PainPoint) -> str:
        """Enhance the problem statement for impact."""
        quantifiers = [
            "wastes 5+ hours weekly",
            "costs companies $50K+ annually",
            "leads to 30% efficiency loss",
        ]
        return f"{pain_point.description} - this {random.choice(quantifiers)}"
    
    def _generate_solution(self, pain_point: PainPoint, trend: str) -> str:
        """Generate a compelling solution description."""
        return (
            f"AI-powered platform that eliminates {pain_point.description[:50].lower()} "
            f"through intelligent automation and {trend.lower()} capabilities"
        )
    
    def _generate_uvp(self, pain_point: PainPoint) -> str:
        """Generate unique value proposition."""
        templates = [
            "Reduce operational costs by 40% while improving quality",
            "Save 10+ hours per week with intelligent automation",
            "Get insights in minutes, not days",
        ]
        return random.choice(templates)
    
    def _optimize_revenue_model(self, pain_point: PainPoint, persona: BuyerPersona) -> RevenueModel:
        """Choose optimal revenue model."""
        if persona.company_size and "1000" in persona.company_size:
            return RevenueModel.ENTERPRISE_LICENSE
        if pain_point.urgency_score > 0.8:
            return RevenueModel.SUBSCRIPTION
        return RevenueModel.FREEMIUM
    
    def _create_pricing_hypothesis(self, persona: BuyerPersona) -> PricingHypothesis:
        """Create pricing hypothesis based on persona."""
        if "enterprise" in persona.company_size.lower() if persona.company_size else False:
            return PricingHypothesis(
                tiers=["Team", "Business", "Enterprise"],
                price_range="$99-$999/month"
            )
        return PricingHypothesis(
            tiers=["Free", "Pro", "Team"],
            price_range="$0-$49/user/month"
        )
    
    def _find_automation_opportunities(self, pain_point: PainPoint) -> List[str]:
        """Find automation opportunities."""
        return [
            "Automated workflow triggers",
            "AI-powered recommendations",
            "Self-healing processes",
            "Smart notifications",
        ][:3]
    
    def _generate_tech_requirements(self, trend: str) -> str:
        """Generate tech requirements summary."""
        return f"Modern cloud-native SaaS with {trend.split()[0]} capabilities"
    
    def _deduplicate_ideas(self, ideas: List[StartupIdea]) -> List[StartupIdea]:
        """Remove duplicate ideas based on name similarity."""
        seen_names = set()
        unique_ideas = []
        
        for idea in ideas:
            name_key = idea.name.lower().replace(" ", "")[:20]
            if name_key not in seen_names:
                seen_names.add(name_key)
                unique_ideas.append(idea)
        
        return unique_ideas
    
    def _enhance_positioning(self, idea: StartupIdea, research: MarketResearch) -> StartupIdea:
        """Enhance idea positioning for market fit."""
        # Add trending technology if not present
        if not any(tech in idea.technical_requirements_summary for tech in ["AI", "ML", "automation"]):
            idea.technical_requirements_summary += " with AI/ML capabilities"
        
        # Ensure differentiators are unique
        if len(idea.differentiation_factors) < 3:
            idea.differentiation_factors.extend([
                "Modern, intuitive UX",
                "Fast implementation",
            ])
        
        return idea
