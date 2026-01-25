#!/usr/bin/env python
"""
Quick unit test for LaunchForge build components
"""

import sys
from src.assistant import ConversationContext, InteractiveAssistant
from src.models import StartupIdea, BuyerPersona, RevenueModel, PricingHypothesis


def test_conversation_context():
    """Test ConversationContext data structure."""
    print("Testing ConversationContext...")
    ctx = ConversationContext()
    
    assert ctx.session_id, "Session ID should be generated"
    assert ctx.started_at, "Start time should be set"
    assert not ctx.is_complete(), "Empty context should not be complete"
    
    # Fill in context
    ctx.raw_idea = "An AI chatbot platform"
    ctx.target_users = "Businesses"
    ctx.key_features = ["AI Chat", "Analytics"]
    ctx.monetization = "Subscription"
    
    assert ctx.is_complete(), "Filled context should be complete"
    print("  ✓ ConversationContext works correctly\n")


def test_fallback_idea_creation():
    """Test that assistant can create a fallback idea when AI parsing fails."""
    print("Testing fallback idea creation...")
    
    assistant = InteractiveAssistant(llm_provider='mock')
    assistant.context.raw_idea = "A social platform for remote workers"
    assistant.context.target_users = "Remote workers"
    assistant.context.key_features = ["Chat", "Video calls", "Project management"]
    assistant.context.unique_value = "Built for distributed teams"
    
    fallback_idea = assistant._create_fallback_idea()
    
    assert isinstance(fallback_idea, StartupIdea), "Should return StartupIdea"
    assert fallback_idea.name, "Idea should have a name"
    assert fallback_idea.one_liner, "Idea should have a one-liner"
    assert len(fallback_idea.differentiation_factors) >= 1, "Should have differentiation factors"
    
    print(f"  ✓ Created fallback idea: {fallback_idea.name}\n")


def test_assistant_initialization():
    """Test that assistant initializes correctly."""
    print("Testing InteractiveAssistant initialization...")
    
    assistant = InteractiveAssistant(
        llm_provider='mock',
        output_dir='./test_output',
        theme='Modern',
        verbose=False
    )
    
    assert assistant.llm_provider == 'mock', "Provider should be set"
    assert assistant.output_dir == './test_output', "Output dir should be set"
    assert assistant.theme == 'Modern', "Theme should be set"
    assert assistant.context, "Context should be initialized"
    
    print("  ✓ Assistant initializes correctly\n")


def test_idea_model_validation():
    """Test that generated ideas are valid Pydantic models."""
    print("Testing idea model validation...")
    
    # Create a valid idea
    idea = StartupIdea(
        name="TestApp",
        one_liner="A test application",
        problem_statement="Problem statement",
        solution_description="Solution description",
        target_buyer_persona=BuyerPersona(
            title="Test User",
            company_size="small",
            industry="Technology",
            budget_authority=True,
            pain_intensity=0.8
        ),
        value_proposition="Great value",
        revenue_model=RevenueModel.SUBSCRIPTION,
        pricing_hypothesis=PricingHypothesis(
            tiers=["Free", "Pro"],
            price_range="$0-$99/mo"
        ),
        tam_estimate="$1B",
        sam_estimate="$100M",
        som_estimate="$10M",
        technical_requirements_summary="Modern web stack",
    )
    
    assert idea.id, "Idea should have UUID"
    assert idea.revenue_model == RevenueModel.SUBSCRIPTION, "Revenue model should be set"
    
    # Verify JSON serialization works
    idea_json = idea.model_dump(mode='json')
    assert isinstance(idea_json, dict), "Should serialize to JSON"
    
    print(f"  ✓ Idea model validation passed\n")


def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("LAUNCHFORGE BUILD COMPONENT TESTS")
    print("=" * 80 + "\n")
    
    tests = [
        test_conversation_context,
        test_fallback_idea_creation,
        test_assistant_initialization,
        test_idea_model_validation,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"  ✗ {test.__name__} failed: {e}\n")
            failed += 1
        except Exception as e:
            print(f"  ✗ {test.__name__} error: {e}\n")
            failed += 1
    
    print("=" * 80)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 80 + "\n")
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
