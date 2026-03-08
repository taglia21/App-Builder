"""
Ignara Code Generation System v2.

Modules:
    architect    — Intelligent Architecture Designer (idea → SystemSpec)
    engine_v2    — LLM-Powered Code Generator (SystemSpec → complete codebase)
    quality      — Code Quality Pipeline (validation + auto-fix)
    pipeline     — Orchestration Pipeline (architect → generate → validate → fix)
    refinement   — Iterative Refinement Engine (natural language code changes)
    routes       — FastAPI routes for the v2 pipeline API

Legacy modules (v1, template-based):
    engine           — Original template-based generator
    enhanced_engine  — Enhanced template generator with limited LLM
    file_templates   — Backend template strings
    frontend_templates — Frontend template strings
"""

from src.code_generation.architect import SystemArchitect, SystemSpec
from src.code_generation.engine_v2 import CodeGeneratorV2, GenerationResult
from src.code_generation.pipeline import GenerationPipeline, PipelineResult
from src.code_generation.quality import CodeQualityPipeline, AutoFixer, QualityReport
from src.code_generation.refinement import RefinementEngine, RefinementResult

__all__ = [
    "SystemArchitect",
    "SystemSpec",
    "CodeGeneratorV2",
    "GenerationResult",
    "GenerationPipeline",
    "PipelineResult",
    "CodeQualityPipeline",
    "AutoFixer",
    "QualityReport",
    "RefinementEngine",
    "RefinementResult",
]
