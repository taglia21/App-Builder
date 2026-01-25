"""
Startup Generator - Multi-LLM Automated Startup Generation Engine
"""

__version__ = "1.0.0"

# Expose the interactive assistant as a key feature
from .assistant import InteractiveAssistant, run_build_assistant

__all__ = [
    "__version__",
    "InteractiveAssistant",
    "run_build_assistant",
]
