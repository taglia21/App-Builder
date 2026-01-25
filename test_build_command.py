#!/usr/bin/env python
"""
Test script for the LaunchForge build command
Tests the interactive assistant with mock input
"""

import sys
import asyncio
from unittest.mock import patch
from io import StringIO

from src.assistant import InteractiveAssistant


def test_build_command():
    """Test the build command with mock user input."""
    print("\n" + "=" * 80)
    print("TESTING: LaunchForge Build Command")
    print("=" * 80 + "\n")
    
    # Create mock input that simulates user responses
    mock_inputs = [
        # Step 1: Raw idea
        "An AI-powered platform that helps small businesses automate their customer support using intelligent chatbots with natural language processing.",
        # Step 2: Market validation will use LLM
        "yes",  # Confirm to proceed after validation
        # Step 3: Follow-up questions
        "Small business owners (1-50 employees) and customer support teams",  # Target users
        "Smart chatbot, Analytics dashboard, Integration hub",  # Key features
        "1",  # Subscription model
        "24/7 automated support reduces costs by 70%",  # Unique value
        # Step 4: Idea model generation - auto-generated
        "yes",  # Confirm to generate app
        # Step 5: Code generation
        "1",  # Modern theme
        # Final: Deploy now?
        "no",  # Don't deploy in test
    ]
    
    input_iter = iter(mock_inputs)
    
    def mock_input(prompt=""):
        """Mock input function that returns test data."""
        try:
            response = next(input_iter)
            print(f"  → {response}")
            return response
        except StopIteration:
            print("  [Test completed - no more input]")
            sys.exit(0)
    
    # Patch the input function
    with patch('builtins.input', side_effect=mock_input):
        assistant = InteractiveAssistant(
            llm_provider='mock',  # Use mock provider to avoid API calls
            output_dir='./output/test-build',
            theme='Modern',
            verbose=False,
        )
        
        try:
            result = assistant.run()
            
            if result:
                print("\n" + "=" * 80)
                print("✓ BUILD TEST PASSED")
                print("=" * 80)
                print(f"Generated idea: {assistant.context.startup_idea.name if assistant.context.startup_idea else 'N/A'}")
                if assistant.context.output_path:
                    print(f"Output path: {assistant.context.output_path}")
                return True
            else:
                print("\n" + "=" * 80)
                print("✗ BUILD TEST FAILED: Assistant returned False")
                print("=" * 80)
                return False
                
        except KeyboardInterrupt:
            print("\nTest interrupted")
            return False
        except Exception as e:
            print(f"\n✗ BUILD TEST FAILED: {e}")
            import traceback
            traceback.print_exc()
            return False


if __name__ == "__main__":
    success = test_build_command()
    sys.exit(0 if success else 1)
