"""
Idea generation module.
"""

from .engine import IdeaGenerationEngine

try:
    from .llm_engine import LLMIdeaGenerationEngine
except ImportError:
    LLMIdeaGenerationEngine = None

__all__ = ["IdeaGenerationEngine", "LLMIdeaGenerationEngine"]
