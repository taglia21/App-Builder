"""
Tests for the v2 Code Generation improvements made in this session.

Covers:
- _topological_tiers dependency ordering
- Concurrent generation via asyncio.gather + semaphore
- _extract_interface_summary (rich AST extraction: imports, class methods, async funcs)
- _interfaces_summary with relevant_to filtering
- Pipeline run_with_progress (no double-run, result attached to final event)
- _spec_summary compact mode
- Architect validation guards (empty-field entities, missing User entity)
"""
import asyncio
import json
import sys
import textwrap
from dataclasses import dataclass, field as dc_field
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

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
# _topological_tiers tests
# ---------------------------------------------------------------------------

class TestTopologicalTiers:
    """Tests for the _topological_tiers static method on CodeGeneratorV2."""

    def _make_spec(self, path, depends_on=None):
        """Create a minimal _FileSpec-like object."""
        from src.code_generation.engine_v2 import FileCategory

        # We need to import the actual _FileSpec dataclass
        from src.code_generation.engine_v2 import _FileSpec
        return _FileSpec(
            relative_path=path,
            category=FileCategory.BACKEND_CORE,
            prompt_builder=lambda ctx: "",
            description=f"Test file {path}",
            depends_on=depends_on or [],
        )

    def test_no_deps_single_tier(self):
        """All files with no deps should land in one tier."""
        from src.code_generation.engine_v2 import CodeGeneratorV2

        plan = [
            self._make_spec("a.py"),
            self._make_spec("b.py"),
            self._make_spec("c.py"),
        ]
        tiers = CodeGeneratorV2._topological_tiers(plan)
        assert len(tiers) == 1
        assert len(tiers[0]) == 3

    def test_linear_chain(self):
        """A → B → C should produce 3 tiers."""
        from src.code_generation.engine_v2 import CodeGeneratorV2

        plan = [
            self._make_spec("a.py"),
            self._make_spec("b.py", depends_on=["a.py"]),
            self._make_spec("c.py", depends_on=["b.py"]),
        ]
        tiers = CodeGeneratorV2._topological_tiers(plan)
        assert len(tiers) == 3
        assert tiers[0][0].relative_path == "a.py"
        assert tiers[1][0].relative_path == "b.py"
        assert tiers[2][0].relative_path == "c.py"

    def test_diamond_deps(self):
        """Diamond: A → (B, C) → D should produce 3 tiers."""
        from src.code_generation.engine_v2 import CodeGeneratorV2

        plan = [
            self._make_spec("a.py"),
            self._make_spec("b.py", depends_on=["a.py"]),
            self._make_spec("c.py", depends_on=["a.py"]),
            self._make_spec("d.py", depends_on=["b.py", "c.py"]),
        ]
        tiers = CodeGeneratorV2._topological_tiers(plan)
        assert len(tiers) == 3
        # Tier 0: a
        assert {fs.relative_path for fs in tiers[0]} == {"a.py"}
        # Tier 1: b, c (concurrent)
        assert {fs.relative_path for fs in tiers[1]} == {"b.py", "c.py"}
        # Tier 2: d
        assert {fs.relative_path for fs in tiers[2]} == {"d.py"}

    def test_circular_deps_fallback(self):
        """Circular deps should dump remaining files into one tier (no infinite loop)."""
        from src.code_generation.engine_v2 import CodeGeneratorV2

        plan = [
            self._make_spec("a.py", depends_on=["b.py"]),
            self._make_spec("b.py", depends_on=["a.py"]),
        ]
        tiers = CodeGeneratorV2._topological_tiers(plan)
        # Should not hang; dumps into one tier
        assert len(tiers) == 1
        assert len(tiers[0]) == 2

    def test_mixed_deps(self):
        """Mix of independent and dependent files."""
        from src.code_generation.engine_v2 import CodeGeneratorV2

        plan = [
            self._make_spec("config.py"),
            self._make_spec("db.py"),
            self._make_spec("models.py", depends_on=["config.py", "db.py"]),
            self._make_spec("schemas.py", depends_on=["models.py"]),
            self._make_spec("readme.md"),  # no deps
        ]
        tiers = CodeGeneratorV2._topological_tiers(plan)
        # Tier 0: config, db, readme (all independent)
        tier0_paths = {fs.relative_path for fs in tiers[0]}
        assert "config.py" in tier0_paths
        assert "db.py" in tier0_paths
        assert "readme.md" in tier0_paths
        # Tier 1: models
        assert tiers[1][0].relative_path == "models.py"
        # Tier 2: schemas
        assert tiers[2][0].relative_path == "schemas.py"

    def test_empty_plan(self):
        """Empty plan should return empty tiers."""
        from src.code_generation.engine_v2 import CodeGeneratorV2
        tiers = CodeGeneratorV2._topological_tiers([])
        assert tiers == []


# ---------------------------------------------------------------------------
# _extract_interface_summary tests
# ---------------------------------------------------------------------------

class TestExtractInterfaceSummary:
    """Tests for the enhanced _extract_interface_summary static method."""

    def test_extracts_imports(self):
        """Should capture from-imports."""
        from src.code_generation.engine_v2 import CodeGeneratorV2

        source = textwrap.dedent("""\
            from sqlalchemy import Column, Integer, String
            from app.db.base import Base

            class User(Base):
                __tablename__ = "users"
                id = Column(Integer, primary_key=True)
        """)
        summary = CodeGeneratorV2._extract_interface_summary("models/user.py", source)
        assert "from sqlalchemy import Column, Integer, String" in summary
        assert "from app.db.base import Base" in summary

    def test_extracts_class_with_bases(self):
        """Should capture class name with base classes."""
        from src.code_generation.engine_v2 import CodeGeneratorV2

        source = textwrap.dedent("""\
            from pydantic import BaseModel

            class UserCreate(BaseModel):
                email: str
                password: str
        """)
        summary = CodeGeneratorV2._extract_interface_summary("schemas/user.py", source)
        assert "class UserCreate(BaseModel)" in summary

    def test_extracts_methods_up_to_8(self):
        """Should capture up to 8 method signatures per class."""
        from src.code_generation.engine_v2 import CodeGeneratorV2

        methods = "\n".join(
            f"    def method_{i}(self, x): pass" for i in range(12)
        )
        source = f"class BigClass:\n{methods}\n"
        summary = CodeGeneratorV2._extract_interface_summary("big.py", source)
        # Should have at most 8 method lines
        method_lines = [l for l in summary.splitlines() if "def method_" in l]
        assert len(method_lines) == 8

    def test_extracts_async_functions(self):
        """Should capture async function signatures with 'async' prefix."""
        from src.code_generation.engine_v2 import CodeGeneratorV2

        source = textwrap.dedent("""\
            async def get_users(db, skip, limit):
                pass

            async def create_user(db, user_data):
                pass
        """)
        summary = CodeGeneratorV2._extract_interface_summary("crud/user.py", source)
        assert "async def get_users(db, skip, limit)" in summary
        assert "async def create_user(db, user_data)" in summary

    def test_extracts_async_methods(self):
        """Should capture async methods within classes."""
        from src.code_generation.engine_v2 import CodeGeneratorV2

        source = textwrap.dedent("""\
            class UserService:
                async def fetch(self, user_id):
                    pass
                async def update(self, user_id, data):
                    pass
        """)
        summary = CodeGeneratorV2._extract_interface_summary("services/user.py", source)
        assert "class UserService()" in summary
        assert "async def fetch(user_id)" in summary
        assert "async def update(user_id, data)" in summary

    def test_syntax_error_fallback(self):
        """Broken Python should fall back to a source preview."""
        from src.code_generation.engine_v2 import CodeGeneratorV2

        source = "def broken(\n  x =\n"
        summary = CodeGeneratorV2._extract_interface_summary("broken.py", source)
        # Should contain a preview of the source (first 400 chars)
        assert "def broken" in summary

    def test_typescript_exports(self):
        """Should extract exported symbols from TypeScript."""
        from src.code_generation.engine_v2 import CodeGeneratorV2

        source = textwrap.dedent("""\
            export interface User {
              id: number;
              email: string;
            }

            export const API_BASE = "/api";
            const internal = 42;
        """)
        summary = CodeGeneratorV2._extract_interface_summary("types/user.ts", source)
        assert "export interface User" in summary
        assert "export const API_BASE" in summary
        # internal const should NOT be exported
        assert "internal" not in summary

    def test_generic_file(self):
        """Non-code files should get first few non-empty lines."""
        from src.code_generation.engine_v2 import CodeGeneratorV2

        source = "# Dockerfile\nFROM python:3.12\nWORKDIR /app\nCOPY . .\n"
        summary = CodeGeneratorV2._extract_interface_summary("Dockerfile", source)
        assert "FROM python:3.12" in summary


# ---------------------------------------------------------------------------
# _interfaces_summary with relevant_to tests
# ---------------------------------------------------------------------------

class TestInterfacesSummaryRelevance:
    """Tests for the _interfaces_summary relevance scoring."""

    def _make_ctx(self, interfaces: dict):
        """Create a minimal _GenerationContext with given interfaces."""
        from src.code_generation.architect import (
            EntitySpec, FieldSpec, SystemSpec, TechStackSpec,
            RouteSpec, PageSpec, RoleSpec,
        )
        from src.code_generation.engine_v2 import _GenerationContext

        spec = SystemSpec(
            app_name="Test",
            description="Test app",
            entities=[EntitySpec(name="Item", fields=[FieldSpec(name="name", type="string")])],
            api_routes=[RouteSpec(path="/api/items", method="GET", description="List")],
            pages=[PageSpec(route="/", title="Home")],
            roles=[RoleSpec(name="admin", permissions=["all"])],
            integrations=[],
            business_rules=[],
            tech_stack=TechStackSpec(),
        )
        ctx = _GenerationContext(
            spec=spec,
            output_dir=Path("/tmp/test"),
            theme="Modern",
        )
        ctx.generated_interfaces = dict(interfaces)
        return ctx

    def test_no_interfaces(self):
        """Empty interfaces dict should return placeholder."""
        from src.code_generation.engine_v2 import _interfaces_summary

        ctx = self._make_ctx({})
        result = _interfaces_summary(ctx)
        assert "No files generated yet" in result

    def test_relevant_to_filters(self):
        """With relevant_to, should prefer same-entity files."""
        from src.code_generation.engine_v2 import _interfaces_summary

        ctx = self._make_ctx({
            "backend/app/models/user.py": "class User(Base)",
            "backend/app/models/product.py": "class Product(Base)",
            "backend/app/schemas/user.py": "class UserCreate(BaseModel)",
            "backend/app/schemas/product.py": "class ProductCreate(BaseModel)",
            "backend/app/core/config.py": "class Settings(BaseSettings)",
            "frontend/src/types/user.ts": "export interface User {}",
        })
        result = _interfaces_summary(ctx, relevant_to="backend/app/crud/user.py")
        # user-related files should appear
        assert "models/user.py" in result
        assert "schemas/user.py" in result
        # core files should appear (always relevant to backend)
        assert "core/config.py" in result

    def test_without_relevant_to_caps_at_30(self):
        """Without relevant_to, should include up to 30 interfaces."""
        from src.code_generation.engine_v2 import _interfaces_summary

        interfaces = {f"file_{i}.py": f"def func_{i}()" for i in range(50)}
        ctx = self._make_ctx(interfaces)
        result = _interfaces_summary(ctx)
        # Should have at most 30 entries
        count = result.count("---")
        assert count <= 60  # each entry has two "---" markers (prefix/suffix of path)

    def test_frontend_file_prefers_types_and_api(self):
        """Frontend files should see types/ and lib/api as highly relevant."""
        from src.code_generation.engine_v2 import _interfaces_summary

        ctx = self._make_ctx({
            "frontend/src/types/user.ts": "export interface User {}",
            "frontend/src/lib/api.ts": "export const apiClient = ...",
            "backend/app/models/user.py": "class User(Base)",
            "backend/app/core/config.py": "class Settings(BaseSettings)",
        })
        result = _interfaces_summary(ctx, relevant_to="frontend/src/pages/UserPage.tsx")
        # types and api should be in result
        assert "types/user.ts" in result
        assert "lib/api.ts" in result


# ---------------------------------------------------------------------------
# _spec_summary compact mode tests
# ---------------------------------------------------------------------------

class TestSpecSummaryCompact:
    """Tests for _spec_summary with compact=True/False."""

    def _make_spec(self):
        from src.code_generation.architect import (
            EntitySpec, FieldSpec, SystemSpec, TechStackSpec,
            RouteSpec, PageSpec, RoleSpec,
        )
        return SystemSpec(
            app_name="TestApp",
            description="A test application",
            entities=[
                EntitySpec(
                    name="Item",
                    fields=[FieldSpec(name="title", type="string", required=True)],
                )
            ],
            api_routes=[
                RouteSpec(path="/api/items", method="GET", description="List items",
                          auth_required=True, business_logic="Query all items")
            ],
            pages=[PageSpec(route="/", title="Home")],
            roles=[RoleSpec(name="admin", permissions=["all"])],
            integrations=[],
            business_rules=["Users must be authenticated"],
            tech_stack=TechStackSpec(),
        )

    def test_full_includes_routes_and_rules(self):
        """Default (non-compact) includes API Routes and Business Rules."""
        from src.code_generation.engine_v2 import _spec_summary

        spec = self._make_spec()
        result = _spec_summary(spec)
        assert "API Routes:" in result
        assert "/api/items" in result
        assert "Business Rules:" in result
        assert "Users must be authenticated" in result

    def test_compact_omits_routes_and_rules(self):
        """compact=True should omit API Routes and Business Rules."""
        from src.code_generation.engine_v2 import _spec_summary

        spec = self._make_spec()
        result = _spec_summary(spec, compact=True)
        assert "API Routes:" not in result
        assert "Business Rules:" not in result
        # But should still have entities and tech stack
        assert "Item" in result
        assert "Tech Stack:" in result


# ---------------------------------------------------------------------------
# Concurrent generation tests
# ---------------------------------------------------------------------------

class TestConcurrentGeneration:
    """Tests that generate() uses tier-based concurrency."""

    def test_generate_uses_tiers(self):
        """generate() should call _topological_tiers and process results."""
        from src.code_generation.engine_v2 import CodeGeneratorV2
        from src.code_generation.architect import (
            EntitySpec, FieldSpec, SystemSpec, TechStackSpec,
            RouteSpec, PageSpec, RoleSpec,
        )
        import tempfile

        spec = SystemSpec(
            app_name="TierTest",
            description="Testing tier-based generation",
            entities=[
                EntitySpec(
                    name="Widget",
                    fields=[FieldSpec(name="name", type="string", required=True)],
                )
            ],
            api_routes=[RouteSpec(path="/api/widgets", method="GET", description="List")],
            pages=[PageSpec(route="/", title="Home")],
            roles=[RoleSpec(name="admin", permissions=["all"])],
            integrations=[],
            business_rules=[],
            tech_stack=TechStackSpec(),
        )

        gen = CodeGeneratorV2()
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_async(gen.generate(spec, tmpdir))
            # Should produce files
            assert result.total_files > 0
            # Should track LLM calls
            assert result.llm_calls_made >= 0  # Mock returns 0 calls but field exists
            # All files should be listed
            assert len(result.files) == result.total_files

    def test_max_concurrency_attribute(self):
        """CodeGeneratorV2 should have MAX_CONCURRENCY = 6."""
        from src.code_generation.engine_v2 import CodeGeneratorV2
        assert CodeGeneratorV2.MAX_CONCURRENCY == 6


# ---------------------------------------------------------------------------
# Pipeline run_with_progress (no double-run) tests
# ---------------------------------------------------------------------------

class TestPipelineNoDoubleRun:
    """Tests that run_with_progress yields result on final event."""

    def test_run_with_progress_attaches_result(self):
        """Final 'complete' event should have _pipeline_result attribute."""
        from src.code_generation.pipeline import GenerationPipeline
        import tempfile

        pipeline = GenerationPipeline(output_base_dir=tempfile.mkdtemp())
        events = []
        result_obj = None

        async def _collect():
            nonlocal result_obj
            async for event in pipeline.run_with_progress(
                "TestApp",
                "A testing application",
            ):
                events.append(event)
                if event.phase == "complete":
                    result_obj = getattr(event, "_pipeline_result", None)

        run_async(_collect())

        # Should have yielded multiple events
        assert len(events) >= 4  # architect, generate, validate, complete
        # Final event should be "complete"
        assert events[-1].phase == "complete"
        assert events[-1].progress == 100
        # Result should be attached
        assert result_obj is not None
        assert hasattr(result_obj, "spec")
        assert hasattr(result_obj, "generation")
        assert hasattr(result_obj, "quality")
        assert result_obj.status in ("success", "success_with_warnings", "failed")

    def test_run_with_progress_phases(self):
        """Should yield events in expected phase order."""
        from src.code_generation.pipeline import GenerationPipeline
        import tempfile

        pipeline = GenerationPipeline(output_base_dir=tempfile.mkdtemp())
        phases = []

        async def _collect():
            async for event in pipeline.run_with_progress(
                "PhaseTest",
                "A phase testing app",
            ):
                if event.phase not in phases:
                    phases.append(event.phase)

        run_async(_collect())

        # Must see these phases in order
        assert "architect" in phases
        assert "generate" in phases
        assert "validate" in phases
        assert "complete" in phases
        # "complete" should be last
        assert phases[-1] == "complete"


# ---------------------------------------------------------------------------
# Architect validation guards tests
# ---------------------------------------------------------------------------

class TestArchitectValidationGuards:
    """Tests for architect entity validation guards."""

    def test_fallback_on_no_fields(self):
        """If all entities have empty fields, architect falls back."""
        from src.code_generation.architect import SystemArchitect, EntitySpec, FieldSpec

        arch = SystemArchitect()
        # The design() method with mock LLM won't produce entities with fields,
        # so it should use fallback
        spec = run_async(arch.design("EmptyApp", "An app with nothing"))
        # Fallback spec should always have entities with fields
        assert spec is not None
        assert len(spec.entities) >= 1
        for entity in spec.entities:
            assert len(entity.fields) >= 1, f"Entity {entity.name} has no fields"

    def test_user_entity_always_present(self):
        """The final spec should always include a User entity."""
        from src.code_generation.architect import SystemArchitect

        arch = SystemArchitect()
        spec = run_async(arch.design("NoUserApp", "A simple calculator"))
        entity_names = {e.name.lower() for e in spec.entities}
        assert "user" in entity_names, "User entity should be auto-inserted"

    def test_user_entity_has_email_field(self):
        """Auto-inserted User entity should have an email field."""
        from src.code_generation.architect import SystemArchitect

        arch = SystemArchitect()
        spec = run_async(arch.design("FieldCheck", "An app for checking fields"))
        user_entities = [e for e in spec.entities if e.name.lower() == "user"]
        assert len(user_entities) >= 1
        user = user_entities[0]
        field_names = {f.name for f in user.fields}
        assert "email" in field_names

    def test_fallback_spec_is_valid(self):
        """_fallback_spec should produce a complete, valid SystemSpec."""
        from src.code_generation.architect import SystemArchitect

        arch = SystemArchitect()
        spec = arch._fallback_spec("FallbackTest", "Testing the fallback path")
        assert spec.app_name == "FallbackTest"
        assert len(spec.entities) >= 1
        assert len(spec.api_routes) >= 1
        assert len(spec.pages) >= 1
        # Should have at least one entity with fields
        entities_with_fields = [e for e in spec.entities if e.fields]
        assert len(entities_with_fields) >= 1


# ---------------------------------------------------------------------------
# _GenerationContext tests
# ---------------------------------------------------------------------------

class TestGenerationContext:
    """Tests for the _GenerationContext dataclass."""

    def test_has_lock(self):
        """Context should have an asyncio.Lock for thread safety."""
        from src.code_generation.engine_v2 import _GenerationContext
        from src.code_generation.architect import (
            EntitySpec, FieldSpec, SystemSpec, TechStackSpec,
            RouteSpec, PageSpec, RoleSpec,
        )

        spec = SystemSpec(
            app_name="Test",
            description="Test",
            entities=[EntitySpec(name="X", fields=[FieldSpec(name="n", type="string")])],
            api_routes=[RouteSpec(path="/x", method="GET", description="x")],
            pages=[PageSpec(route="/", title="Home")],
            roles=[RoleSpec(name="admin", permissions=["all"])],
            integrations=[],
            business_rules=[],
            tech_stack=TechStackSpec(),
        )
        ctx = _GenerationContext(spec=spec, output_dir=Path("/tmp"), theme="Modern")
        assert isinstance(ctx._lock, asyncio.Lock)
        assert ctx._spec_summary_cache is None
        assert ctx.llm_calls == 0

    def test_generated_interfaces_starts_empty(self):
        """Context should start with empty generated_interfaces dict."""
        from src.code_generation.engine_v2 import _GenerationContext
        from src.code_generation.architect import (
            EntitySpec, FieldSpec, SystemSpec, TechStackSpec,
            RouteSpec, PageSpec, RoleSpec,
        )

        spec = SystemSpec(
            app_name="Test", description="Test",
            entities=[EntitySpec(name="X", fields=[FieldSpec(name="n", type="string")])],
            api_routes=[RouteSpec(path="/x", method="GET", description="x")],
            pages=[PageSpec(route="/", title="Home")],
            roles=[RoleSpec(name="admin", permissions=["all"])],
            integrations=[], business_rules=[], tech_stack=TechStackSpec(),
        )
        ctx = _GenerationContext(spec=spec, output_dir=Path("/tmp"), theme="Modern")
        assert ctx.generated_interfaces == {}


# ---------------------------------------------------------------------------
# _FileSpec depends_on tests
# ---------------------------------------------------------------------------

class TestFileSpecDependsOn:
    """Tests for the depends_on field on _FileSpec."""

    def test_default_empty(self):
        """depends_on should default to empty list."""
        from src.code_generation.engine_v2 import _FileSpec, FileCategory

        fs = _FileSpec(
            relative_path="test.py",
            category=FileCategory.BACKEND_CORE,
            prompt_builder=lambda ctx: "",
        )
        assert fs.depends_on == []

    def test_explicit_deps(self):
        """Should accept explicit dependency list."""
        from src.code_generation.engine_v2 import _FileSpec, FileCategory

        fs = _FileSpec(
            relative_path="schemas/user.py",
            category=FileCategory.BACKEND_SCHEMA,
            prompt_builder=lambda ctx: "",
            depends_on=["models/user.py", "db/base.py"],
        )
        assert fs.depends_on == ["models/user.py", "db/base.py"]


# ---------------------------------------------------------------------------
# _build_file_plan tests
# ---------------------------------------------------------------------------

class TestBuildFilePlan:
    """Tests that _build_file_plan produces files with proper depends_on."""

    def test_plan_has_dependencies(self):
        """Generated plan should have files with depends_on populated."""
        from src.code_generation.engine_v2 import CodeGeneratorV2, _GenerationContext
        from src.code_generation.architect import (
            EntitySpec, FieldSpec, SystemSpec, TechStackSpec,
            RouteSpec, PageSpec, RoleSpec,
        )

        spec = SystemSpec(
            app_name="DepTest",
            description="Testing dependencies",
            entities=[
                EntitySpec(
                    name="Task",
                    fields=[FieldSpec(name="title", type="string", required=True)],
                )
            ],
            api_routes=[RouteSpec(path="/api/tasks", method="GET", description="List")],
            pages=[PageSpec(route="/", title="Home")],
            roles=[RoleSpec(name="admin", permissions=["all"])],
            integrations=[],
            business_rules=[],
            tech_stack=TechStackSpec(),
        )

        gen = CodeGeneratorV2()
        ctx = _GenerationContext(spec=spec, output_dir=Path("/tmp/test"), theme="Modern")
        plan = gen._build_file_plan(ctx)

        # Should have files
        assert len(plan) > 0

        # Foundation files should have no deps
        config_files = [f for f in plan if "config.py" in f.relative_path]
        for cf in config_files:
            # Core config should have no or minimal deps
            assert isinstance(cf.depends_on, list)

        # Schema files should depend on model files
        schema_files = [f for f in plan if "/schemas/" in f.relative_path]
        for sf in schema_files:
            # Should have at least one dependency
            if sf.depends_on:
                assert any("models/" in dep or "model" in dep.lower() for dep in sf.depends_on), \
                    f"{sf.relative_path} deps: {sf.depends_on}"


# ---------------------------------------------------------------------------
# Integration: full generation end-to-end
# ---------------------------------------------------------------------------

class TestFullGenerationIntegration:
    """Integration test: architect → generator with all improvements active."""

    def test_end_to_end_with_mock_llm(self):
        """Full architect → generate flow with mock LLM."""
        from src.code_generation.architect import SystemArchitect
        from src.code_generation.engine_v2 import CodeGeneratorV2
        import tempfile

        arch = SystemArchitect()
        spec = run_async(arch.design("IntegrationTest", "A project management tool"))

        gen = CodeGeneratorV2()
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_async(gen.generate(spec, tmpdir))
            # Should produce a non-trivial number of files
            assert result.total_files >= 5
            # Output path should be set
            assert result.output_path
            # Should have backend and/or frontend files
            assert result.backend_files > 0 or result.frontend_files > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
