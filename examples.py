#!/usr/bin/env python3
"""
Example: How to use the Startup Generator programmatically
"""

import asyncio
from src.config import load_config
from src.pipeline import StartupGenerationPipeline
from src.models import BuyerPersona, PricingHypothesis, RevenueModel, StartupIdea
from uuid import uuid4


async def example_full_pipeline():
    """Example: Run the full pipeline."""
    print("=" * 80)
    print("EXAMPLE 1: Full Pipeline Execution")
    print("=" * 80)
    
    # Load configuration
    config = load_config("config.yml")
    
    # Create pipeline
    pipeline = StartupGenerationPipeline(config)
    
    # Run complete pipeline
    result = await pipeline.run()
    
    # Access results
    print(f"\n✓ Generated {len(result.ideas.ideas)} ideas")
    print(f"✓ Selected: {result.selected_idea.name}")
    print(f"✓ Score: {result.evaluation.evaluated_ideas[0].total_score:.2f}")
    print(f"✓ Codebase: {result.generated_codebase.output_path}")
    print(f"✓ Files: {result.generated_codebase.files_generated}")
    
    return result


async def example_custom_idea():
    """Example: Build from a custom idea."""
    print("\n" + "=" * 80)
    print("EXAMPLE 2: Build from Custom Idea")
    print("=" * 80)
    
    # Create a custom startup idea
    idea = StartupIdea(
        id=uuid4(),
        name="AI Meeting Assistant",
        one_liner="Automate meeting notes and action items with AI",
        problem_statement="Teams waste time taking meeting notes and tracking action items",
        solution_description="AI-powered tool that automatically transcribes meetings, "
                            "generates summaries, and tracks action items",
        target_buyer_persona=BuyerPersona(
            title="VP of Operations",
            company_size="100-1000 employees",
            industry="software",
            budget_authority=True,
            pain_intensity=0.85,
        ),
        value_proposition="Save 5+ hours per week on meeting administration",
        revenue_model=RevenueModel.SUBSCRIPTION,
        pricing_hypothesis=PricingHypothesis(
            tiers=["Starter", "Team", "Enterprise"],
            price_range="$19-$199/month",
        ),
        tam_estimate="$2B",
        sam_estimate="$500M",
        som_estimate="$25M",
        competitive_landscape=["Otter.ai", "Fireflies.ai"],
        differentiation_factors=[
            "Better AI accuracy",
            "Slack/Teams integration",
            "Action item tracking",
        ],
        automation_opportunities=[
            "Auto-transcription",
            "Smart summaries",
            "Action item assignment",
        ],
        technical_requirements_summary="Web app with speech-to-text AI and NLP",
        source_pain_point_ids=[],
    )
    
    # Load config and create pipeline
    config = load_config("config.yml")
    pipeline = StartupGenerationPipeline(config)
    
    # Build from this idea
    result = await pipeline.run_from_idea(idea)
    
    print(f"\n✓ Built product for: {idea.name}")
    print(f"✓ Codebase: {result.generated_codebase.output_path}")
    
    return result


async def example_intelligence_only():
    """Example: Just gather intelligence."""
    print("\n" + "=" * 80)
    print("EXAMPLE 3: Intelligence Gathering Only")
    print("=" * 80)
    
    from src.intelligence import IntelligenceGatheringEngine
    
    config = load_config("config.yml")
    engine = IntelligenceGatheringEngine(config)
    
    # Gather intelligence
    intelligence = await engine.gather()
    
    print(f"\n✓ Pain points: {len(intelligence.pain_points)}")
    print(f"✓ Emerging industries: {len(intelligence.emerging_industries)}")
    print(f"✓ Opportunities: {len(intelligence.opportunity_categories)}")
    
    # Show top pain points
    if intelligence.pain_points:
        print("\nTop 3 Pain Points:")
        for i, pp in enumerate(intelligence.pain_points[:3], 1):
            print(f"{i}. [{pp.source_type.value}] {pp.description[:100]}...")
            print(f"   Urgency: {pp.urgency_score:.2f}, Frequency: {pp.frequency_count}")
    
    return intelligence


async def example_ideas_from_intelligence():
    """Example: Generate ideas from intelligence data."""
    print("\n" + "=" * 80)
    print("EXAMPLE 4: Generate Ideas from Intelligence")
    print("=" * 80)
    
    from src.intelligence import IntelligenceGatheringEngine
    from src.idea_generation import IdeaGenerationEngine
    
    config = load_config("config.yml")
    
    # Gather intelligence
    intel_engine = IntelligenceGatheringEngine(config)
    intelligence = await intel_engine.gather()
    
    # Generate ideas
    idea_engine = IdeaGenerationEngine(config)
    ideas = await idea_engine.generate(intelligence)
    
    print(f"\n✓ Generated {len(ideas.ideas)} ideas")
    
    # Show top 5 ideas
    print("\nTop 5 Ideas:")
    for i, idea in enumerate(ideas.ideas[:5], 1):
        print(f"{i}. {idea.name}")
        print(f"   {idea.one_liner}")
        print(f"   Revenue: {idea.revenue_model.value}")
        print()
    
    return ideas


async def example_score_ideas():
    """Example: Score and rank ideas."""
    print("\n" + "=" * 80)
    print("EXAMPLE 5: Score and Rank Ideas")
    print("=" * 80)
    
    from src.intelligence import IntelligenceGatheringEngine
    from src.idea_generation import IdeaGenerationEngine
    from src.scoring import ScoringEngine
    
    config = load_config("config.yml")
    
    # Gather intelligence and generate ideas
    intel_engine = IntelligenceGatheringEngine(config)
    intelligence = await intel_engine.gather()
    
    idea_engine = IdeaGenerationEngine(config)
    ideas = await idea_engine.generate(intelligence)
    
    # Score ideas
    scoring_engine = ScoringEngine(config)
    evaluation = await scoring_engine.evaluate(ideas, intelligence)
    
    print(f"\n✓ Evaluated {len(evaluation.evaluated_ideas)} ideas")
    
    # Show top 5 scored ideas
    print("\nTop 5 Scored Ideas:")
    for eval_idea in evaluation.evaluated_ideas[:5]:
        idea = next(i for i in ideas.ideas if i.id == eval_idea.idea_id)
        print(f"{eval_idea.rank}. {idea.name} - Score: {eval_idea.total_score:.2f}")
        print(f"   Market Demand: {eval_idea.scores.market_demand.score}/10")
        print(f"   Urgency: {eval_idea.scores.urgency.score}/10")
        print(f"   Time to MVP: {eval_idea.scores.time_to_mvp.score}/10")
        print()
    
    return evaluation


async def main():
    """Run all examples."""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "STARTUP GENERATOR EXAMPLES" + " " * 32 + "║")
    print("╚" + "=" * 78 + "╝")
    
    # Note: These examples require valid API keys in .env
    # Comment out examples you don't want to run
    
    try:
        # Example 3: Quick intelligence test
        await example_intelligence_only()
        
        # Example 4: Generate ideas from intelligence
        # await example_ideas_from_intelligence()
        
        # Example 5: Score and rank ideas
        # await example_score_ideas()
        
        # Example 2: Build from custom idea
        # await example_custom_idea()
        
        # Example 1: Full pipeline (takes 30-45 minutes!)
        # await example_full_pipeline()
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        print("\nNote: Make sure you have:")
        print("  1. Created .env file with API keys")
        print("  2. Configured config.yml")
        print("  3. Installed all requirements")
    
    print("\n" + "=" * 80)
    print("Examples completed!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
