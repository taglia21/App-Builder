"""
Scoring and Evaluation Engine for ranking startup ideas.
"""

from datetime import timezone, datetime
from typing import Dict, List
from uuid import UUID

from loguru import logger

from ..config import PipelineConfig
from ..models import (
    DimensionScore,
    EvaluatedIdea,
    EvaluationReport,
    IdeaCatalog,
    IdeaScores,
    IntelligenceData,
    RevenueModel,
    StartupIdea,
)


class ScoringEngine:
    """Engine for evaluating and scoring startup ideas."""

    def __init__(self, config: PipelineConfig):
        """Initialize the scoring engine."""
        self.config = config
        self.weights = config.scoring.weights if config.scoring else {}
        self.min_total_score = (
            config.scoring.min_total_score if config.scoring else 70.0
        )

    async def evaluate(
        self, ideas: IdeaCatalog, intelligence: IntelligenceData
    ) -> EvaluationReport:
        """Evaluate and rank all ideas."""
        logger.info(f"Evaluating {len(ideas.ideas)} ideas")

        evaluated_ideas = []

        for idea in ideas.ideas:
            try:
                scores = self._score_idea(idea, intelligence)
                total_score = self._calculate_total_score(scores)

                evaluated = EvaluatedIdea(
                    idea_id=idea.id, scores=scores, total_score=total_score, rank=0
                )

                evaluated_ideas.append(evaluated)

            except Exception as e:
                logger.error(f"Error evaluating idea {idea.name}: {e}")
                continue

        # Sort by total score
        evaluated_ideas.sort(key=lambda x: x.total_score, reverse=True)

        # Assign ranks
        for i, evaluated in enumerate(evaluated_ideas):
            evaluated.rank = i + 1

        # Select top idea
        if evaluated_ideas:
            selected_id = evaluated_ideas[0].idea_id
            selection_reasoning = (
                f"Selected {evaluated_ideas[0].rank}st ranked idea "
                f"with total score of {evaluated_ideas[0].total_score:.2f}"
            )
        else:
            raise ValueError("No ideas could be evaluated")

        logger.info(f"Top idea has score: {evaluated_ideas[0].total_score:.2f}")

        return EvaluationReport(
            evaluation_timestamp=datetime.now(timezone.utc),
            evaluated_ideas=evaluated_ideas,
            selected_idea_id=selected_id,
            selection_reasoning=selection_reasoning,
        )

    def _score_idea(
        self, idea: StartupIdea, intelligence: IntelligenceData
    ) -> IdeaScores:
        """Score an idea across all dimensions."""

        # Market Demand
        market_demand = self._score_market_demand(idea, intelligence)

        # Urgency
        urgency = self._score_urgency(idea, intelligence)

        # Enterprise Value
        enterprise_value = self._score_enterprise_value(idea)

        # Recurring Revenue Potential
        recurring_revenue = self._score_recurring_revenue(idea)

        # Time to MVP
        time_to_mvp = self._score_time_to_mvp(idea)

        # Technical Complexity
        technical_complexity = self._score_technical_complexity(idea)

        # Competition
        competition = self._score_competition(idea)

        # Uniqueness
        uniqueness = self._score_uniqueness(idea)

        # Automation Potential
        automation_potential = self._score_automation_potential(idea)

        return IdeaScores(
            market_demand=market_demand,
            urgency=urgency,
            enterprise_value=enterprise_value,
            recurring_revenue_potential=recurring_revenue,
            time_to_mvp=time_to_mvp,
            technical_complexity=technical_complexity,
            competition=competition,
            uniqueness=uniqueness,
            automation_potential=automation_potential,
        )

    def _score_market_demand(
        self, idea: StartupIdea, intelligence: IntelligenceData
    ) -> DimensionScore:
        """Score market demand (1-10)."""
        # Count related pain points
        related_pain_points = [
            pp
            for pp in intelligence.pain_points
            if pp.id in idea.source_pain_point_ids
        ]

        total_frequency = sum(pp.frequency_count for pp in related_pain_points)

        # Score based on frequency
        if total_frequency > 100:
            score = 10
        elif total_frequency > 50:
            score = 9
        elif total_frequency > 30:
            score = 8
        elif total_frequency > 20:
            score = 7
        elif total_frequency > 10:
            score = 6
        elif total_frequency > 5:
            score = 5
        else:
            score = 4

        justification = (
            f"Based on {len(related_pain_points)} pain points "
            f"with combined frequency of {total_frequency}"
        )

        return DimensionScore(score=score, justification=justification)

    def _score_urgency(
        self, idea: StartupIdea, intelligence: IntelligenceData
    ) -> DimensionScore:
        """Score urgency (1-10)."""
        related_pain_points = [
            pp
            for pp in intelligence.pain_points
            if pp.id in idea.source_pain_point_ids
        ]

        if not related_pain_points:
            return DimensionScore(score=5, justification="No pain point data")

        avg_urgency = sum(pp.urgency_score for pp in related_pain_points) / len(
            related_pain_points
        )

        score = int(avg_urgency * 10)
        score = max(1, min(10, score))

        justification = f"Average urgency score of {avg_urgency:.2f} from pain points"

        return DimensionScore(score=score, justification=justification)

    def _score_enterprise_value(self, idea: StartupIdea) -> DimensionScore:
        """Score enterprise value (1-10)."""
        # Based on buyer persona and company size
        company_size = idea.target_buyer_persona.company_size

        if "5000+" in company_size or "enterprise" in company_size.lower():
            score = 10
        elif "1000" in company_size:
            score = 9
        elif "500" in company_size:
            score = 8
        elif "100" in company_size:
            score = 7
        elif "50" in company_size:
            score = 6
        else:
            score = 5

        # Boost if budget authority
        if idea.target_buyer_persona.budget_authority:
            score = min(10, score + 1)

        justification = (
            f"Target company size: {company_size}, "
            f"Budget authority: {idea.target_buyer_persona.budget_authority}"
        )

        return DimensionScore(score=score, justification=justification)

    def _score_recurring_revenue(self, idea: StartupIdea) -> DimensionScore:
        """Score recurring revenue potential (1-10)."""
        if idea.revenue_model == RevenueModel.SUBSCRIPTION:
            score = 10
            justification = "Subscription-based model with recurring revenue"
        elif idea.revenue_model == RevenueModel.USAGE:
            score = 8
            justification = "Usage-based model with predictable recurring usage"
        elif idea.revenue_model == RevenueModel.HYBRID:
            score = 9
            justification = "Hybrid model combining subscription and usage"
        else:
            score = 5
            justification = "Transaction-based model, less predictable"

        return DimensionScore(score=score, justification=justification)

    def _score_time_to_mvp(self, idea: StartupIdea) -> DimensionScore:
        """Score time to MVP (1-10, higher is faster)."""
        tech_req = idea.technical_requirements_summary.lower()

        # Simple heuristics
        complex_keywords = [
            "machine learning",
            "custom ai",
            "blockchain",
            "iot",
            "hardware",
        ]
        simple_keywords = ["crud", "lightweight", "simple", "standard"]

        is_complex = any(keyword in tech_req for keyword in complex_keywords)
        is_simple = any(keyword in tech_req for keyword in simple_keywords)

        if is_simple:
            score = 9
            justification = "Simple technical requirements, fast to build"
        elif is_complex:
            score = 4
            justification = "Complex technical requirements, longer development time"
        else:
            score = 7
            justification = "Moderate technical requirements"

        return DimensionScore(score=score, justification=justification)

    def _score_technical_complexity(self, idea: StartupIdea) -> DimensionScore:
        """Score technical complexity (1-10, lower is better so higher score = simpler)."""
        tech_req = idea.technical_requirements_summary.lower()

        complex_keywords = [
            "microservices",
            "distributed",
            "custom ml",
            "real-time",
            "video processing",
        ]
        simple_keywords = ["saas", "web app", "api", "standard"]

        is_complex = any(keyword in tech_req for keyword in complex_keywords)
        is_simple = any(keyword in tech_req for keyword in simple_keywords)

        if is_simple:
            score = 9
            justification = "Standard technology stack"
        elif is_complex:
            score = 5
            justification = "Complex architecture required"
        else:
            score = 7
            justification = "Moderate complexity"

        return DimensionScore(score=score, justification=justification)

    def _score_competition(self, idea: StartupIdea) -> DimensionScore:
        """Score competition (1-10, higher is less competition)."""
        # Based on competitive landscape
        num_competitors = len(idea.competitive_landscape)

        if num_competitors == 0:
            score = 10
            justification = "No direct competitors identified"
        elif num_competitors <= 2:
            score = 8
            justification = f"{num_competitors} competitors, space for differentiation"
        elif num_competitors <= 5:
            score = 6
            justification = f"{num_competitors} competitors, competitive market"
        else:
            score = 4
            justification = f"{num_competitors}+ competitors, saturated market"

        return DimensionScore(score=score, justification=justification)

    def _score_uniqueness(self, idea: StartupIdea) -> DimensionScore:
        """Score uniqueness (1-10)."""
        num_diff_factors = len(idea.differentiation_factors)

        if num_diff_factors >= 5:
            score = 10
        elif num_diff_factors >= 3:
            score = 8
        elif num_diff_factors >= 2:
            score = 6
        else:
            score = 4

        justification = (
            f"{num_diff_factors} differentiation factors: "
            f"{', '.join(idea.differentiation_factors[:3])}"
        )

        return DimensionScore(score=score, justification=justification)

    def _score_automation_potential(self, idea: StartupIdea) -> DimensionScore:
        """Score automation potential (1-10)."""
        num_auto_ops = len(idea.automation_opportunities)

        if num_auto_ops >= 5:
            score = 10
        elif num_auto_ops >= 3:
            score = 8
        elif num_auto_ops >= 2:
            score = 6
        else:
            score = 4

        # Boost for AI-related ideas
        if "ai" in idea.name.lower() or "automated" in idea.name.lower():
            score = min(10, score + 2)

        justification = f"{num_auto_ops} automation opportunities identified"

        return DimensionScore(score=score, justification=justification)

    def _calculate_total_score(self, scores: IdeaScores) -> float:
        """Calculate weighted total score."""
        dimensions = {
            "market_demand": scores.market_demand.score,
            "urgency": scores.urgency.score,
            "enterprise_value": scores.enterprise_value.score,
            "recurring_revenue": scores.recurring_revenue_potential.score,
            "time_to_mvp": scores.time_to_mvp.score,
            "technical_complexity": scores.technical_complexity.score,
            "competition": scores.competition.score,
            "uniqueness": scores.uniqueness.score,
            "automation_potential": scores.automation_potential.score,
        }

        total = 0.0
        for dimension, score in dimensions.items():
            weight = self.weights.get(dimension, 0.1)
            total += score * weight * 10  # Scale to 0-100

        return total
