"""
Startup Generator - Multi-LLM Automated Startup Generation Engine
"""

__version__ = "1.0.0"


def __getattr__(name: str):
    """Lazy-load heavy modules only when explicitly accessed.

    This avoids pulling in the entire pipeline/intelligence chain
    (sklearn, textblob, etc.) when the package is imported by the
    dashboard, which never uses InteractiveAssistant.
    """
    if name == "InteractiveAssistant":
        from .assistant import InteractiveAssistant
        return InteractiveAssistant
    if name == "run_build_assistant":
        from .assistant import run_build_assistant
        return run_build_assistant
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "__version__",
    "InteractiveAssistant",
    "run_build_assistant",
]
