"""
Data models for the Startup Generator pipeline.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


# ============================================================================
# Intelligence Models
# ============================================================================


class SourceType(str, Enum):
    """Types of data sources."""

    REDDIT = "reddit"
    TWITTER = "twitter"
    NEWS = "news"
    YOUTUBE = "youtube"
    GITHUB = "github"
    GOOGLE = "google"


class PainPoint(BaseModel):
    """A discovered pain point."""

    id: UUID = Field(default_factory=uuid4)
    description: str
    source_type: SourceType
    source_url: str
    frequency_count: int = 0
    urgency_score: float = Field(ge=0.0, le=1.0)
    sentiment_score: float = Field(ge=-1.0, le=1.0)
    affected_industries: List[str] = Field(default_factory=list)
    affected_user_personas: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    raw_excerpts: List[str] = Field(default_factory=list)


class EmergingIndustry(BaseModel):
    """An emerging industry or market."""

    id: UUID = Field(default_factory=uuid4)
    industry_name: str
    growth_signals: List[str] = Field(default_factory=list)
    funding_activity: str = ""
    key_players: List[str] = Field(default_factory=list)
    technology_stack_trends: List[str] = Field(default_factory=list)
    opportunity_score: float = Field(ge=0.0, le=1.0)


class CompetitionDensity(str, Enum):
    """Competition density levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class OpportunityCategory(BaseModel):
    """A category of business opportunities."""

    category_name: str
    subcategories: List[str] = Field(default_factory=list)
    pain_point_ids: List[UUID] = Field(default_factory=list)
    market_size_estimate: str = ""
    competition_density: CompetitionDensity = CompetitionDensity.MEDIUM
    automation_potential: float = Field(ge=0.0, le=1.0)


class CompetitorAnalysis(BaseModel):
    """Analysis of a competitor."""

    competitor_name: str
    product_url: str
    pricing_model: str = ""
    feature_list: List[str] = Field(default_factory=list)
    user_complaints: List[str] = Field(default_factory=list)
    market_position: str = ""
    vulnerability_gaps: List[str] = Field(default_factory=list)


class IntelligenceData(BaseModel):
    """Complete intelligence gathering output."""

    extraction_timestamp: datetime = Field(default_factory=datetime.utcnow)
    pain_points: List[PainPoint] = Field(default_factory=list)
    emerging_industries: List[EmergingIndustry] = Field(default_factory=list)
    opportunity_categories: List[OpportunityCategory] = Field(default_factory=list)
    competitor_analysis: List[CompetitorAnalysis] = Field(default_factory=list)


# ============================================================================
# Idea Models
# ============================================================================


class RevenueModel(str, Enum):
    """Revenue model types."""

    SUBSCRIPTION = "subscription"
    USAGE = "usage"
    TRANSACTION = "transaction"
    HYBRID = "hybrid"


class BuyerPersona(BaseModel):
    """Target buyer persona."""

    title: str
    company_size: str
    industry: str
    budget_authority: bool = False
    pain_intensity: float = Field(ge=0.0, le=1.0)


class PricingHypothesis(BaseModel):
    """Pricing hypothesis for the product."""

    tiers: List[str] = Field(default_factory=list)
    price_range: str


class StartupIdea(BaseModel):
    """A generated startup idea."""

    id: UUID = Field(default_factory=uuid4)
    name: str
    one_liner: str = Field(max_length=100)
    problem_statement: str
    solution_description: str
    target_buyer_persona: BuyerPersona
    value_proposition: str
    revenue_model: RevenueModel
    pricing_hypothesis: PricingHypothesis
    tam_estimate: str
    sam_estimate: str
    som_estimate: str
    competitive_landscape: List[str] = Field(default_factory=list)
    differentiation_factors: List[str] = Field(default_factory=list)
    automation_opportunities: List[str] = Field(default_factory=list)
    technical_requirements_summary: str
    source_pain_point_ids: List[UUID] = Field(default_factory=list)


class IdeaCatalog(BaseModel):
    """Catalog of generated ideas."""

    generation_timestamp: datetime = Field(default_factory=datetime.utcnow)
    ideas: List[StartupIdea] = Field(default_factory=list)


# ============================================================================
# Scoring Models
# ============================================================================


class DimensionScore(BaseModel):
    """Score for a single dimension."""

    score: int = Field(ge=1, le=10)
    justification: str


class IdeaScores(BaseModel):
    """All dimension scores for an idea."""

    market_demand: DimensionScore
    urgency: DimensionScore
    enterprise_value: DimensionScore
    recurring_revenue_potential: DimensionScore
    time_to_mvp: DimensionScore
    technical_complexity: DimensionScore
    competition: DimensionScore
    uniqueness: DimensionScore
    automation_potential: DimensionScore


class EvaluatedIdea(BaseModel):
    """An idea with its evaluation scores."""

    idea_id: UUID
    scores: IdeaScores
    total_score: float
    rank: int


class EvaluationReport(BaseModel):
    """Complete evaluation report."""

    evaluation_timestamp: datetime = Field(default_factory=datetime.utcnow)
    evaluated_ideas: List[EvaluatedIdea] = Field(default_factory=list)
    selected_idea_id: UUID
    selection_reasoning: str


# ============================================================================
# Prompt Models
# ============================================================================


class ProductPrompt(BaseModel):
    """Generated product development prompt."""

    idea_id: UUID
    idea_name: str
    prompt_content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class RefinementCheck(BaseModel):
    """Result of a refinement check."""

    check_name: str
    passed: bool
    issues: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)


class RefinementIteration(BaseModel):
    """A single refinement iteration."""

    iteration_number: int
    checks: List[RefinementCheck] = Field(default_factory=list)
    changes_made: List[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class CertificationStatus(str, Enum):
    """Certification status."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    GOLD_STANDARD = "gold_standard"
    FAILED = "failed"


class PromptCertification(BaseModel):
    """Certification of a product prompt."""

    status: CertificationStatus
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    iterations_required: int = 0
    checks_passed: List[str] = Field(default_factory=list)
    final_hash: str = ""


class GoldStandardPrompt(BaseModel):
    """A certified gold-standard product prompt."""

    product_prompt: ProductPrompt
    certification: PromptCertification
    refinement_history: List[RefinementIteration] = Field(default_factory=list)


# ============================================================================
# Code Generation Models
# ============================================================================


class GeneratedCodebase(BaseModel):
    """A generated codebase."""

    idea_id: UUID
    idea_name: str
    output_path: str
    backend_framework: str
    frontend_framework: str
    infrastructure_provider: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    files_generated: int = 0
    lines_of_code: int = 0


# ============================================================================
# Pipeline Models
# ============================================================================


class PipelineStage(str, Enum):
    """Pipeline execution stages."""

    INTELLIGENCE = "intelligence"
    IDEA_GENERATION = "idea_generation"
    SCORING = "scoring"
    PROMPT_ENGINEERING = "prompt_engineering"
    REFINEMENT = "refinement"
    CODE_GENERATION = "code_generation"


class PipelineStatus(str, Enum):
    """Pipeline execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class PipelineMetadata(BaseModel):
    """Metadata about pipeline execution."""

    execution_id: UUID = Field(default_factory=uuid4)
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    status: PipelineStatus = PipelineStatus.PENDING
    current_stage: Optional[PipelineStage] = None
    error_message: Optional[str] = None


class PipelineOutput(BaseModel):
    """Complete output from pipeline execution."""

    metadata: PipelineMetadata
    intelligence: Optional[IntelligenceData] = None
    ideas: Optional[IdeaCatalog] = None
    evaluation: Optional[EvaluationReport] = None
    selected_idea: Optional[StartupIdea] = None
    gold_standard_prompt: Optional[GoldStandardPrompt] = None
    generated_codebase: Optional[GeneratedCodebase] = None
