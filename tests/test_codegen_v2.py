"""
Comprehensive tests for the v2 Code Generation System.

Tests the full pipeline: Architect → Generator → Quality → Refinement
Uses the mock LLM client (no API keys needed).
"""
import asyncio
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).parent.parent))


def run_async(coro):
    """Helper to run async code in tests."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ---------------------------------------------------------------------------
# Architect tests
# ---------------------------------------------------------------------------

class TestSystemArchitect:
    """Tests for the SystemArchitect (idea → SystemSpec)."""

    def test_import(self):
        """Architect module imports without errors."""
        from src.code_generation.architect import SystemArchitect, SystemSpec
        assert SystemArchitect is not None
        assert SystemSpec is not None

    def test_spec_models_validate(self):
        """All Pydantic spec models can be instantiated."""
        from src.code_generation.architect import (
            EntitySpec,
            FieldSpec,
            IntegrationSpec,
            PageSpec,
            RelationshipSpec,
            RoleSpec,
            RouteSpec,
            SystemSpec,
            TechStackSpec,
        )
        # Minimal valid SystemSpec
        spec = SystemSpec(
            app_name="TestApp",
            description="A test application",
            entities=[
                EntitySpec(
                    name="Item",
                    fields=[FieldSpec(name="title", type="string", required=True)],
                )
            ],
            api_routes=[
                RouteSpec(path="/api/items", method="GET", description="List items")
            ],
            pages=[PageSpec(route="/", title="Home")],
            roles=[RoleSpec(name="admin", permissions=["all"])],
            integrations=[],
            business_rules=["Users must be authenticated"],
            tech_stack=TechStackSpec(),
        )
        assert spec.app_name == "TestApp"
        assert len(spec.entities) == 1

    def test_entity_spec_auto_fields(self):
        """EntitySpec auto-fills plural and other computed fields."""
        from src.code_generation.architect import EntitySpec, FieldSpec

        entity = EntitySpec(
            name="Product",
            fields=[FieldSpec(name="title", type="string", required=True)],
        )
        # Should have auto-computed plural
        assert entity.plural  # non-empty

    def test_fallback_spec(self):
        """Fallback spec is valid when LLM calls fail."""
        from src.code_generation.architect import SystemArchitect

        arch = SystemArchitect()
        spec = arch._fallback_spec("MyApp", "A project management tool for teams")
        assert spec.app_name == "MyApp"
        assert len(spec.entities) >= 1
        assert len(spec.api_routes) >= 1
        assert len(spec.pages) >= 1

    def test_architect_design_with_mock(self):
        """Architect.design() returns a valid spec even with mock LLM."""
        from src.code_generation.architect import SystemArchitect

        arch = SystemArchitect()
        spec = run_async(
            arch.design("TaskFlow", "A project management tool with task boards and team collaboration")
        )
        assert spec is not None
        assert spec.app_name == "TaskFlow"
        # Even with mock LLM, fallback should produce valid spec
        assert len(spec.entities) >= 1


# ---------------------------------------------------------------------------
# Engine v2 tests
# ---------------------------------------------------------------------------

class TestCodeGeneratorV2:
    """Tests for the v2 code generation engine."""

    def test_import(self):
        """Engine v2 module imports without errors."""
        from src.code_generation.engine_v2 import CodeGeneratorV2, GenerationResult, FileCategory
        assert CodeGeneratorV2 is not None
        assert GenerationResult is not None

    def test_file_category_enum(self):
        """FileCategory enum has expected values."""
        from src.code_generation.engine_v2 import FileCategory
        
        # Should have both backend and frontend categories
        categories = [c.value for c in FileCategory]
        assert any("backend" in c for c in categories)
        assert any("frontend" in c for c in categories)
        assert "infrastructure" in categories

    def test_generation_result_model(self):
        """GenerationResult model validates correctly."""
        from src.code_generation.engine_v2 import GeneratedFile, GenerationResult, FileCategory

        result = GenerationResult(
            output_path="/tmp/test",
            files=[
                GeneratedFile(
                    path="main.py",
                    lines=50,
                    category=FileCategory.BACKEND_CORE,
                    llm_generated=True,
                )
            ],
            total_files=1,
            total_lines=50,
            backend_files=1,
            frontend_files=0,
            generation_time_seconds=5.0,
            llm_calls_made=1,
            warnings=[],
        )
        assert result.total_files == 1


# ---------------------------------------------------------------------------
# Quality pipeline tests
# ---------------------------------------------------------------------------

class TestQualityPipeline:
    """Tests for the code quality validation pipeline."""

    def test_import(self):
        """Quality module imports without errors."""
        from src.code_generation.quality import (
            AutoFixer,
            CodeQualityPipeline,
            QualityCheck,
            QualityReport,
        )
        assert CodeQualityPipeline is not None

    def test_quality_check_model(self):
        """QualityCheck model works correctly."""
        from src.code_generation.quality import QualityCheck

        check = QualityCheck(
            name="syntax_check",
            category="syntax",
            passed=True,
            severity="info",
            message="All files pass syntax check",
        )
        assert check.passed is True

    def test_python_syntax_check(self):
        """Python syntax checker catches errors."""
        from src.code_generation.quality import CodeQualityPipeline

        pipeline = CodeQualityPipeline()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Write a valid Python file
            good_file = Path(tmpdir) / "good.py"
            good_file.write_text("x = 1\nprint(x)\n")

            # Write an invalid Python file
            bad_file = Path(tmpdir) / "bad.py"
            bad_file.write_text("def foo(\n  x =\n")

            # Call via validate() which converts to Path properly
            checks = run_async(pipeline._check_python_syntax(Path(tmpdir)))

            # Should have at least one failure
            failed = [c for c in checks if not c.passed]
            passed = [c for c in checks if c.passed]
            assert len(failed) >= 1
            assert any("bad.py" in (c.file_path or "") for c in failed)

    def test_security_check(self):
        """Security checker catches hardcoded secrets."""
        from src.code_generation.quality import CodeQualityPipeline

        pipeline = CodeQualityPipeline()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Write a file with a hardcoded password
            bad_file = Path(tmpdir) / "config.py"
            bad_file.write_text('password = "mysecretpassword123"\napi_key = "sk-1234567890"\n')

            checks = run_async(pipeline._check_security(Path(tmpdir)))

            # Should flag security issues
            security_issues = [c for c in checks if not c.passed]
            assert len(security_issues) >= 1

    def test_file_structure_check(self):
        """File structure check validates directory layout."""
        from src.code_generation.quality import CodeQualityPipeline

        pipeline = CodeQualityPipeline()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create proper structure
            (Path(tmpdir) / "backend" / "app").mkdir(parents=True)
            (Path(tmpdir) / "frontend" / "src").mkdir(parents=True)
            (Path(tmpdir) / "README.md").write_text("# Test")
            (Path(tmpdir) / ".env.example").write_text("KEY=value")

            checks = run_async(pipeline._check_file_structure(Path(tmpdir)))

            passed = [c for c in checks if c.passed]
            assert len(passed) >= 2  # At least README and some dirs exist

    def test_full_validate(self):
        """Full validate() works end-to-end."""
        from src.code_generation.quality import CodeQualityPipeline

        pipeline = CodeQualityPipeline()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create minimal valid project
            (Path(tmpdir) / "backend" / "app").mkdir(parents=True)
            (Path(tmpdir) / "frontend" / "src").mkdir(parents=True)
            (Path(tmpdir) / "backend" / "app" / "main.py").write_text(
                "from fastapi import FastAPI\napp = FastAPI()\n"
            )
            (Path(tmpdir) / "README.md").write_text("# Test")
            (Path(tmpdir) / ".env.example").write_text("KEY=value")

            report = run_async(pipeline.validate(tmpdir))
            assert report is not None
            assert isinstance(report.score, int)
            assert 0 <= report.score <= 100


# ---------------------------------------------------------------------------
# Pipeline tests
# ---------------------------------------------------------------------------

class TestGenerationPipeline:
    """Tests for the main orchestration pipeline."""

    def test_import(self):
        """Pipeline module imports without errors."""
        from src.code_generation.pipeline import GenerationPipeline, PipelineResult
        assert GenerationPipeline is not None
        assert PipelineResult is not None

    def test_pipeline_instantiation(self):
        """Pipeline can be instantiated."""
        from src.code_generation.pipeline import GenerationPipeline

        pipeline = GenerationPipeline(output_base_dir="/tmp/test_ignara")
        assert pipeline.architect is not None
        assert pipeline.generator is not None
        assert pipeline.quality is not None


# ---------------------------------------------------------------------------
# Refinement tests
# ---------------------------------------------------------------------------

class TestRefinementEngine:
    """Tests for the iterative refinement engine."""

    def test_import(self):
        """Refinement module imports without errors."""
        from src.code_generation.refinement import (
            FileChange,
            RefinementEngine,
            RefinementHistory,
            RefinementRequest,
            RefinementResult,
        )
        assert RefinementEngine is not None

    def test_scope_detection(self):
        """Scope detection correctly classifies instructions."""
        from src.code_generation.refinement import RefinementEngine

        engine = RefinementEngine()

        # Backend-focused instructions
        assert engine._detect_scope("Add a new field to the User model") in ("backend", "full")
        assert engine._detect_scope("Create a new API endpoint for products") in ("backend", "full")

        # Frontend-focused instructions
        assert engine._detect_scope("Change the button color to blue") in ("frontend", "full")
        assert engine._detect_scope("Add a new page for the dashboard") in ("frontend", "full")

    def test_project_tree(self):
        """Project tree generation works."""
        from src.code_generation.refinement import RefinementEngine

        engine = RefinementEngine()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create some files
            (Path(tmpdir) / "backend").mkdir()
            (Path(tmpdir) / "backend" / "main.py").write_text("app = FastAPI()")
            (Path(tmpdir) / "frontend").mkdir()
            (Path(tmpdir) / "frontend" / "page.tsx").write_text("export default function() {}")

            tree = engine._get_project_tree(tmpdir)
            assert "main.py" in tree
            assert "page.tsx" in tree

    def test_refinement_history(self):
        """Refinement history tracks changes."""
        from src.code_generation.refinement import (
            FileChange,
            RefinementHistory,
            RefinementRequest,
            RefinementResult,
        )

        history = RefinementHistory()

        with tempfile.TemporaryDirectory() as tmpdir:
            request = RefinementRequest(
                instruction="Add a rating field",
                project_path=tmpdir,
            )
            result = RefinementResult(
                files_modified=[
                    FileChange(
                        path="models.py",
                        change_type="modified",
                        diff_summary="Added rating field",
                    )
                ],
                explanation="Added rating field to models.py",
            )

            history.add(request, result)
            entries = history.get_history(tmpdir)
            assert len(entries) >= 1


# ---------------------------------------------------------------------------
# Routes tests
# ---------------------------------------------------------------------------

class TestRoutes:
    """Tests for the API routes."""

    def test_import(self):
        """Routes module imports and creates a router."""
        from src.code_generation.routes import router
        assert router is not None
        # Check routes are registered
        route_paths = [r.path for r in router.routes]
        assert any("/generate" in p for p in route_paths)


# ---------------------------------------------------------------------------
# Integration test
# ---------------------------------------------------------------------------

class TestIntegration:
    """Integration tests verifying the full module interconnection."""

    def test_init_exports(self):
        """The __init__.py exports all key classes."""
        from src.code_generation import (
            AutoFixer,
            CodeGeneratorV2,
            CodeQualityPipeline,
            GenerationPipeline,
            GenerationResult,
            PipelineResult,
            QualityReport,
            RefinementEngine,
            RefinementResult,
            SystemArchitect,
            SystemSpec,
        )
        # All should be importable
        assert SystemArchitect is not None
        assert CodeGeneratorV2 is not None
        assert GenerationPipeline is not None

    def test_architect_to_spec_dict(self):
        """SystemSpec can be serialized to dict for passing to other modules."""
        from src.code_generation.architect import SystemArchitect

        arch = SystemArchitect()
        spec = run_async(
            arch.design("ShopEasy", "An e-commerce platform for small businesses")
        )

        # Should be serializable
        spec_dict = spec.model_dump()
        assert isinstance(spec_dict, dict)
        assert "entities" in spec_dict
        assert "api_routes" in spec_dict
        assert "tech_stack" in spec_dict

    def test_end_to_end_architect_to_quality(self):
        """Full flow: architect designs spec, quality pipeline validates output dir."""
        from src.code_generation.architect import SystemArchitect
        from src.code_generation.quality import CodeQualityPipeline

        arch = SystemArchitect()
        spec = run_async(
            arch.design("BlogEngine", "A blogging platform with comments and tags")
        )

        # Create a minimal project structure from the spec
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create structure based on spec
            (Path(tmpdir) / "backend" / "app" / "models").mkdir(parents=True)
            (Path(tmpdir) / "backend" / "app" / "schemas").mkdir(parents=True)
            (Path(tmpdir) / "frontend" / "src").mkdir(parents=True)
            (Path(tmpdir) / "README.md").write_text(f"# {spec.app_name}")
            (Path(tmpdir) / ".env.example").write_text("SECRET_KEY=change-me")

            # Write a model file for each entity
            for entity in spec.entities:
                model_name = entity.name.lower()
                model_file = Path(tmpdir) / "backend" / "app" / "models" / f"{model_name}.py"
                model_file.write_text(f"# {entity.name} model\nclass {entity.name}:\n    pass\n")

            # Run quality checks
            pipeline = CodeQualityPipeline()
            report = run_async(pipeline.validate(tmpdir, spec.model_dump()))

            assert report is not None
            assert isinstance(report.score, int)
            # Should have some checks run
            assert len(report.checks) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
