"""LLM-powered scoring engine for evaluating startup ideas."""

import asyncio
import json
import logging
from datetime import datetime, timezone

from src.llm import get_llm_client
from src.models import (
    DimensionScore,
    EvaluatedIdea,
    EvaluationReport,
    IdeaCatalog,
    IdeaScores,
    IntelligenceData,
)
from src.scoring.engine import ScoringEngine

logger = logging.getLogger(__name__)

SCORING_SYSTEM_PROMPT = """You are an expert startup evaluator and venture capital analyst. 
Score startup ideas on a 1-10 scale across multiple dimensions. Be rigorous and honest.
Return your evaluation as a JSON object."""

SCORING_USER_PROMPT = """Evaluate this startup idea:

Name: {name}
One-liner: {one_liner}
Problem: {problem}
Solution: {solution}
Target Customer: {target_customer}
Revenue Model: {revenue_model}
Value Proposition: {value_prop}

Score each dimension from 1-10 and provide a brief justification:

Return ONLY a JSON object with this exact structure:
{{
    "market_demand": {{"score": <1-10>, "justification": "<why>"}},
    "urgency": {{"score": <1-10>, "justification": "<why>"}},
    "enterprise_value": {{"score": <1-10>, "justification": "<why>"}},
    "recurring_revenue_potential": {{"score": <1-10>, "justification": "<why>"}},
    "time_to_mvp": {{"score": <1-10>, "justification": "<why>"}},
    "technical_complexity": {{"score": <1-10>, "justification": "<why>"}},
    "competition": {{"score": <1-10>, "justification": "<why>"}},
    "uniqueness": {{"score": <1-10>, "justification": "<why>"}},
    "automation_potential": {{"score": <1-10>, "justification": "<why>"}}
}}"""


class LLMScoringEngine:
    """Scores startup ideas using LLM analysis with heuristic fallback."""

    def __init__(self, config, llm_provider: str = "groq"):
        self.config = config
        self.llm = get_llm_client(llm_provider)
        self.weights = config.scoring.weights if config.scoring else {}
        self.fallback_engine = ScoringEngine(config)

    async def evaluate(
        self, ideas: IdeaCatalog, intelligence: IntelligenceData
    ) -> EvaluationReport:
        """Evaluate and rank all ideas using LLM."""
        logger.info(f"Evaluating {len(ideas.ideas)} ideas with LLM scoring")

        evaluated_ideas = []
        for idea in ideas.ideas:
            try:
                scores = await self._score_idea_llm(idea)
                if scores is None:
                    # Fallback to heuristic
                    scores = self.fallback_engine._score_idea(idea, intelligence)

                total_score = self._calculate_total_score(scores)
                evaluated = EvaluatedIdea(
                    idea_id=idea.id, scores=scores, total_score=total_score, rank=0
                )
                evaluated_ideas.append(evaluated)

            except Exception as e:
                logger.error(f"Error evaluating idea {idea.name}: {e}")
                # Try heuristic fallback for this idea
                try:
                    scores = self.fallback_engine._score_idea(idea, intelligence)
                    total_score = self._calculate_total_score(scores)
                    evaluated = EvaluatedIdea(
                        idea_id=idea.id, scores=scores, total_score=total_score, rank=0
                    )
                    evaluated_ideas.append(evaluated)
                except Exception:
                    continue

        if not evaluated_ideas:
            logger.warning("LLM scoring failed entirely, falling back to heuristic engine")
            return await self.fallback_engine.evaluate(ideas, intelligence)

        # Sort by total score
        evaluated_ideas.sort(key=lambda x: x.total_score, reverse=True)
        for i, evaluated in enumerate(evaluated_ideas):
            evaluated.rank = i + 1

        selected_id = evaluated_ideas[0].idea_id
        selection_reasoning = (
            f"LLM-evaluated: Selected #1 ranked idea "
            f"with score {evaluated_ideas[0].total_score:.2f}"
        )

        return EvaluationReport(
            evaluation_timestamp=datetime.now(timezone.utc),
            evaluated_ideas=evaluated_ideas,
            selected_idea_id=selected_id,
            selection_reasoning=selection_reasoning,
        )

    def _score_idea_llm_sync(self, idea) -> "IdeaScores | None":
        """Synchronous implementation of LLM idea scoring (called via executor)."""
        prompt = SCORING_USER_PROMPT.format(
            name=idea.name,
            one_liner=idea.one_liner,
            problem=idea.problem_statement,
            solution=idea.solution_description,
            target_customer=idea.target_buyer_persona.title if idea.target_buyer_persona else "Unknown",
            revenue_model=idea.revenue_model.value if hasattr(idea.revenue_model, 'value') else str(idea.revenue_model),
            value_prop=idea.value_proposition,
        )

        response = self.llm.complete(
            prompt=prompt,
            system_prompt=SCORING_SYSTEM_PROMPT,
            max_tokens=1500,
            temperature=0.3,
            json_mode=False,
        )

        # Parse JSON from response
        content = response.content
        start = content.find("{")
        end = content.rfind("}") + 1
        if start == -1 or end <= start:
            return None

        data = json.loads(content[start:end])

        return IdeaScores(
            market_demand=DimensionScore(
                score=max(1, min(10, data["market_demand"]["score"])),
                justification=data["market_demand"]["justification"],
            ),
            urgency=DimensionScore(
                score=max(1, min(10, data["urgency"]["score"])),
                justification=data["urgency"]["justification"],
            ),
            enterprise_value=DimensionScore(
                score=max(1, min(10, data["enterprise_value"]["score"])),
                justification=data["enterprise_value"]["justification"],
            ),
            recurring_revenue_potential=DimensionScore(
                score=max(1, min(10, data["recurring_revenue_potential"]["score"])),
                justification=data["recurring_revenue_potential"]["justification"],
            ),
            time_to_mvp=DimensionScore(
                score=max(1, min(10, data["time_to_mvp"]["score"])),
                justification=data["time_to_mvp"]["justification"],
            ),
            technical_complexity=DimensionScore(
                score=max(1, min(10, data["technical_complexity"]["score"])),
                justification=data["technical_complexity"]["justification"],
            ),
            competition=DimensionScore(
                score=max(1, min(10, data["competition"]["score"])),
                justification=data["competition"]["justification"],
            ),
            uniqueness=DimensionScore(
                score=max(1, min(10, data["uniqueness"]["score"])),
                justification=data["uniqueness"]["justification"],
            ),
            automation_potential=DimensionScore(
                score=max(1, min(10, data["automation_potential"]["score"])),
                justification=data["automation_potential"]["justification"],
            ),
        )

    async def _score_idea_llm(self, idea) -> "IdeaScores | None":
        """Score a single idea using LLM (async wrapper using executor to avoid blocking event loop)."""
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self._score_idea_llm_sync, idea)
            return result
        except Exception as e:
            logger.warning(f"LLM scoring failed for {idea.name}: {e}")
            return None

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
            total += score * weight * 10

        return total
