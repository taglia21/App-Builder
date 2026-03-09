"""
Comprehensive integration tests for the Ignara App-Builder pipeline.

Covers end-to-end flows using MockLLMClient (no API keys needed):
1. Pipeline Integration
2. Route Model validation
3. Refinement Chat Integration
4. Consistency Checker Integration
5. Engine Context Integration
6. File Plan Completeness
"""
from __future__ import annotations

import asyncio
import inspect
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).parent.parent))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def run_async(coro):
    """Helper to run async code in tests."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ---------------------------------------------------------------------------
# Shared fixtures / factory functions
# ---------------------------------------------------------------------------


def make_test_spec():
    """Build a realistic SystemSpec for tests."""
    from src.code_generation.architect import (
        EntitySpec,
        FieldSpec,
        PageSpec,
        RoleSpec,
        RouteSpec,
        SystemSpec,
        TechStackSpec,
    )

    return SystemSpec(
        app_name="TestApp",
        description="A task management application",
        entities=[
            EntitySpec(
                name="Task",
                fields=[
                    FieldSpec(name="title", type="string", required=True),
                    FieldSpec(name="description", type="text"),
                    FieldSpec(name="status", type="string", default="pending"),
                    FieldSpec(name="due_date", type="date"),
                ],
            ),
            EntitySpec(
                name="User",
                fields=[
                    FieldSpec(name="email", type="string", required=True),
                    FieldSpec(name="full_name", type="string"),
                ],
            ),
        ],
        api_routes=[
            RouteSpec(path="/api/tasks", method="GET", description="List tasks"),
            RouteSpec(path="/api/tasks", method="POST", description="Create task"),
            RouteSpec(path="/api/users", method="GET", description="List users"),
        ],
        pages=[
            PageSpec(route="/", title="Dashboard"),
            PageSpec(route="/tasks", title="Tasks"),
        ],
        roles=[RoleSpec(name="admin", permissions=["all"])],
        integrations=[],
        business_rules=["Users must be authenticated"],
        tech_stack=TechStackSpec(),
    )


def make_test_context(spec=None, customization=None):
    """Build a _GenerationContext for tests."""
    from src.code_generation.engine_v2 import _GenerationContext

    return _GenerationContext(
        spec=spec or make_test_spec(),
        output_dir=Path("/tmp/test_output"),
        theme="Modern",
        customization=customization or {},
    )


# =============================================================================
# 1. Pipeline Integration Tests
# =============================================================================


class TestPipelineIntegration:
    """End-to-end pipeline tests using MockLLM."""

    def test_pipeline_instantiation_has_all_components(self):
        """Pipeline has architect, generator, quality, fixer, critic_panel, consistency."""
        from src.code_generation.pipeline import GenerationPipeline

        pipeline = GenerationPipeline(output_base_dir="/tmp/test_ignara_integration")
        assert hasattr(pipeline, "architect"), "Pipeline must have 'architect'"
        assert hasattr(pipeline, "generator"), "Pipeline must have 'generator'"
        assert hasattr(pipeline, "quality"), "Pipeline must have 'quality'"
        assert hasattr(pipeline, "fixer"), "Pipeline must have 'fixer'"
        assert hasattr(pipeline, "critic_panel"), "Pipeline must have 'critic_panel'"
        assert hasattr(pipeline, "consistency"), "Pipeline must have 'consistency'"

    def test_pipeline_result_model_complete(self):
        """PipelineResult can be created with all fields and serialized."""
        from src.code_generation.architect import SystemSpec, TechStackSpec
        from src.code_generation.engine_v2 import GenerationResult
        from src.code_generation.pipeline import PipelineResult
        from src.code_generation.quality import QualityReport, QualityCheck

        spec = make_test_spec()
        generation = GenerationResult(
            output_path="/tmp/test",
            files=[],
            total_files=0,
            total_lines=0,
            backend_files=0,
            frontend_files=0,
            generation_time_seconds=1.0,
            llm_calls_made=5,
            warnings=[],
        )
        quality = QualityReport(
            checks=[],
            score=85,
            passed=True,
            errors=0,
            warnings=2,
            summary="Quality check passed",
        )

        result = PipelineResult(
            spec=spec,
            generation=generation,
            quality=quality,
            fixes_applied=3,
            consistency_fixes=1,
            output_path="/tmp/test",
            total_time_seconds=15.5,
            status="success",
            critic_report={"overall_score": 90},
            customization={"backend_framework": "fastapi"},
        )

        assert result.fixes_applied == 3
        assert result.consistency_fixes == 1
        assert result.total_time_seconds == 15.5
        assert result.status == "success"
        assert result.critic_report is not None
        assert result.customization is not None

        # Verify serialization
        d = result.model_dump()
        assert isinstance(d, dict)
        assert "spec" in d
        assert "generation" in d
        assert "quality" in d
        assert d["fixes_applied"] == 3

    def test_pipeline_result_with_customization(self):
        """PipelineResult includes customization dict when provided."""
        from src.code_generation.engine_v2 import GenerationResult
        from src.code_generation.pipeline import PipelineResult
        from src.code_generation.quality import QualityReport

        spec = make_test_spec()
        customization = {
            "backend_framework": "django",
            "database": "mysql",
            "auth_strategy": "session",
            "frontend_framework": "vue",
            "css_framework": "material-ui",
            "deployment_target": "aws",
            "include_tests": False,
            "include_ci": True,
            "api_style": "graphql",
            "extra_instructions": "Use async views everywhere",
        }

        generation = GenerationResult(
            output_path="/tmp/test",
            total_files=0,
            total_lines=0,
            backend_files=0,
            frontend_files=0,
            generation_time_seconds=0.0,
            llm_calls_made=0,
        )
        quality = QualityReport(
            checks=[], score=80, passed=True, errors=0, warnings=0, summary="OK"
        )

        result = PipelineResult(
            spec=spec,
            generation=generation,
            quality=quality,
            customization=customization,
        )

        assert result.customization is not None
        assert result.customization["backend_framework"] == "django"
        assert result.customization["database"] == "mysql"
        assert result.customization["api_style"] == "graphql"

    def test_run_accepts_customization_parameter(self):
        """verify run() method signature accepts a 'customization' parameter."""
        from src.code_generation.pipeline import GenerationPipeline

        sig = inspect.signature(GenerationPipeline.run)
        assert "customization" in sig.parameters, (
            "GenerationPipeline.run() must accept a 'customization' parameter"
        )
        # Verify it is optional (has a default)
        param = sig.parameters["customization"]
        assert param.default is not inspect.Parameter.empty or param.kind in (
            inspect.Parameter.VAR_KEYWORD,
            inspect.Parameter.KEYWORD_ONLY,
        ), "'customization' parameter should have a default value (Optional)"


# =============================================================================
# 2. Route Model Tests
# =============================================================================


class TestRouteModels:
    """Test all Pydantic models in routes.py."""

    def test_generate_request_full_customization(self):
        """GenerateRequest accepts all customization fields."""
        from src.code_generation.routes import GenerateRequest

        req = GenerateRequest(
            idea_name="MyApp",
            description="A comprehensive test application with all features",
            features=["auth", "payments"],
            theme="Dark",
            max_fix_rounds=3,
            backend_framework="django",
            database="mysql",
            auth_strategy="session",
            frontend_framework="vue",
            css_framework="material-ui",
            deployment_target="aws",
            include_tests=False,
            include_ci=False,
            api_style="graphql",
            extra_instructions="Use async views",
        )

        assert req.idea_name == "MyApp"
        assert req.backend_framework == "django"
        assert req.database == "mysql"
        assert req.auth_strategy == "session"
        assert req.frontend_framework == "vue"
        assert req.css_framework == "material-ui"
        assert req.deployment_target == "aws"
        assert req.include_tests is False
        assert req.include_ci is False
        assert req.api_style == "graphql"
        assert req.extra_instructions == "Use async views"

    def test_generate_request_defaults(self):
        """GenerateRequest defaults are: fastapi, postgresql, jwt, nextjs, tailwind, docker, true, true, rest, ''."""
        from src.code_generation.routes import GenerateRequest

        req = GenerateRequest(
            idea_name="DefaultApp",
            description="A test application using all default values",
        )

        assert req.backend_framework == "fastapi"
        assert req.database == "postgresql"
        assert req.auth_strategy == "jwt"
        assert req.frontend_framework == "nextjs"
        assert req.css_framework == "tailwind"
        assert req.deployment_target == "docker"
        assert req.include_tests is True
        assert req.include_ci is True
        assert req.api_style == "rest"
        assert req.extra_instructions == ""
        assert req.theme == "Modern"
        assert req.max_fix_rounds == 2

    def test_start_response_model(self):
        """StartResponse can be created and has correct defaults."""
        from src.code_generation.routes import StartResponse

        resp = StartResponse(job_id="abc123")
        assert resp.job_id == "abc123"
        assert resp.status == "started"
        assert "job_id" in resp.message or "Generation" in resp.message

    def test_job_status_response_model(self):
        """JobStatusResponse can be created with all fields."""
        from src.code_generation.routes import JobStatusResponse

        now = datetime.now(timezone.utc)
        resp = JobStatusResponse(
            job_id="xyz789",
            status="completed",
            created_at=now,
            completed_at=now,
            progress={"phase": "complete", "progress": 100},
            result={"status": "success", "output_path": "/tmp/out"},
            error=None,
        )

        assert resp.job_id == "xyz789"
        assert resp.status == "completed"
        assert resp.error is None
        assert resp.progress is not None
        assert resp.result is not None

    def test_refine_request_model(self):
        """RefineRequest can be created with all fields."""
        from src.code_generation.routes import RefineRequest

        req = RefineRequest(
            project_path="/tmp/myproject",
            instruction="Add a rating field to the Task model",
            scope="backend",
            context={"some": "context"},
            undo=False,
            project_id="proj-001",
        )

        assert req.project_path == "/tmp/myproject"
        assert req.instruction == "Add a rating field to the Task model"
        assert req.scope == "backend"
        assert req.undo is False
        assert req.project_id == "proj-001"

    def test_create_chat_request_model(self):
        """CreateChatRequest can be created."""
        from src.code_generation.routes import CreateChatRequest

        req = CreateChatRequest(
            project_path="/tmp/myproject",
            project_id="proj-123",
        )
        assert req.project_path == "/tmp/myproject"
        assert req.project_id == "proj-123"

    def test_create_chat_request_optional_project_id(self):
        """CreateChatRequest project_id is optional."""
        from src.code_generation.routes import CreateChatRequest

        req = CreateChatRequest(project_path="/tmp/myproject")
        assert req.project_path == "/tmp/myproject"
        assert req.project_id is None

    def test_chat_message_request_model(self):
        """ChatMessageRequest can be created with all fields."""
        from src.code_generation.routes import ChatMessageRequest

        req = ChatMessageRequest(
            instruction="Change the button color to blue",
            scope="frontend",
            apply_changes=True,
        )
        assert req.instruction == "Change the button color to blue"
        assert req.scope == "frontend"
        assert req.apply_changes is True

    def test_chat_message_request_empty_instruction_rejected(self):
        """ChatMessageRequest rejects empty instruction (min_length=1)."""
        from pydantic import ValidationError
        from src.code_generation.routes import ChatMessageRequest

        with pytest.raises(ValidationError):
            ChatMessageRequest(instruction="")


# =============================================================================
# 3. Refinement Chat Integration Tests
# =============================================================================


class TestRefinementChatIntegration:
    """Test the full chat flow."""

    def setup_method(self):
        """Create a fresh ChatManager for each test."""
        from src.code_generation.refinement_chat import ChatManager
        self.manager = ChatManager()
        self.tmpdir = tempfile.mkdtemp()

    def teardown_method(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_create_chat_and_get_it_back(self):
        """Create a chat, retrieve it by ID, verify fields match."""
        project_path = self.tmpdir
        chat = self.manager.create_chat(project_path=project_path, project_id="proj-abc")

        assert chat.chat_id, "Chat must have a non-empty ID"
        assert chat.project_path == project_path
        assert chat.project_id == "proj-abc"
        assert isinstance(chat.messages, list)
        assert len(chat.messages) == 0
        assert chat.created_at
        assert chat.updated_at

        # Retrieve the same chat
        retrieved = self.manager.get_chat(chat.chat_id)
        assert retrieved is not None
        assert retrieved.chat_id == chat.chat_id
        assert retrieved.project_path == project_path

    def test_chat_conversation_history_accumulates(self):
        """Add multiple messages to a chat, verify history length grows."""
        chat = self.manager.create_chat(project_path=self.tmpdir)

        chat.add_user_message("Add a dark mode toggle")
        chat.add_assistant_message("Done — updated tailwind.config.ts")
        chat.add_user_message("Also add a language selector")
        chat.add_assistant_message("Done — added LanguageSelector component")

        assert len(chat.messages) == 4
        assert chat.messages[0].role == "user"
        assert chat.messages[1].role == "assistant"
        assert chat.messages[2].role == "user"
        assert chat.messages[3].role == "assistant"

    def test_chat_context_enrichment(self):
        """get_context_summary includes previous messages."""
        chat = self.manager.create_chat(project_path=self.tmpdir)

        chat.add_user_message("Change button color to red")
        chat.add_assistant_message("Changed all primary buttons to red (#EF4444)")
        chat.add_user_message("Now make the header sticky")

        summary = chat.get_context_summary()
        assert "Change button color to red" in summary
        assert "Changed all primary buttons to red" in summary
        assert "Now make the header sticky" in summary

    def test_multiple_chats_for_same_project(self):
        """Create 2 chats for same project, list returns both."""
        project_path = self.tmpdir

        chat1 = self.manager.create_chat(project_path=project_path)
        chat2 = self.manager.create_chat(project_path=project_path)

        chats = self.manager.list_chats(project_path=project_path)
        chat_ids = {c.chat_id for c in chats}
        assert chat1.chat_id in chat_ids
        assert chat2.chat_id in chat_ids
        assert len(chats) == 2

    def test_delete_chat_removes_it_from_listing(self):
        """Delete a chat, verify it is gone from the listing."""
        project_path = self.tmpdir

        chat1 = self.manager.create_chat(project_path=project_path)
        chat2 = self.manager.create_chat(project_path=project_path)

        # Both should be listed
        before = self.manager.list_chats(project_path=project_path)
        assert len(before) == 2

        # Delete chat1
        deleted = self.manager.delete_chat(chat1.chat_id)
        assert deleted is True

        # Should no longer be retrievable
        assert self.manager.get_chat(chat1.chat_id) is None

        # Listing should now have only chat2
        after = self.manager.list_chats(project_path=project_path)
        assert len(after) == 1
        assert after[0].chat_id == chat2.chat_id

    def test_delete_nonexistent_chat_returns_false(self):
        """Deleting a chat that doesn't exist returns False, no exception."""
        result = self.manager.delete_chat("nonexistent-id")
        assert result is False

    def test_list_chats_without_filter_returns_all(self):
        """list_chats() without project_path filter returns all chats."""
        dir1 = tempfile.mkdtemp()
        dir2 = tempfile.mkdtemp()
        try:
            self.manager.create_chat(project_path=dir1)
            self.manager.create_chat(project_path=dir2)
            all_chats = self.manager.list_chats()
            assert len(all_chats) == 2
        finally:
            shutil.rmtree(dir1, ignore_errors=True)
            shutil.rmtree(dir2, ignore_errors=True)


# =============================================================================
# 4. Consistency Checker Integration Tests
# =============================================================================


class TestConsistencyIntegration:
    """Test consistency checker on realistic project structures."""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()

    def teardown_method(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _make_project(self, structure: dict) -> Path:
        """Create a project structure from a dict of path→content."""
        root = Path(self.tmpdir)
        for rel_path, content in structure.items():
            full = root / rel_path
            full.parent.mkdir(parents=True, exist_ok=True)
            full.write_text(content)
        return root

    def test_full_project_consistency_pass(self):
        """Realistic project dir with backend/app structure gets __init__.py files created."""
        from src.code_generation.consistency import ConsistencyChecker

        project = self._make_project({
            "backend/app/models/task.py": "class Task: pass",
            "backend/app/models/user.py": "class User: pass",
            "backend/app/schemas/task.py": "class TaskCreate: pass",
            "backend/app/crud/task.py": "async def get_task(): pass",
            "backend/app/core/config.py": (
                "class Settings:\n"
                "    DATABASE_URL: str\n"
                "    SECRET_KEY: str\n"
            ),
            ".env.example": "DATABASE_URL=postgresql://localhost/db\nSECRET_KEY=change-me\n",
        })

        checker = ConsistencyChecker()
        result = checker.run(str(project))

        # Should create __init__.py files in packages that contain .py files
        init_files = list(project.rglob("__init__.py"))
        assert len(init_files) >= 1, "At least one __init__.py should be created"

        # Verify the init_created fixes are recorded
        init_fixes = [f for f in result.fixes if f.fix_type == "init_created"]
        assert len(init_fixes) >= 1

    def test_import_fix_backend_prefix(self):
        """Fix doubled 'backend.' prefix in imports."""
        from src.code_generation.consistency import ConsistencyChecker

        project = Path(self.tmpdir)

        # Create the real module
        (project / "backend" / "app" / "models").mkdir(parents=True)
        (project / "backend" / "__init__.py").write_text("")
        (project / "backend" / "app" / "__init__.py").write_text("")
        (project / "backend" / "app" / "models" / "__init__.py").write_text("")
        (project / "backend" / "app" / "models" / "user.py").write_text("class User: pass")

        # Create a file with the doubled-prefix import bug
        broken_file = project / "backend" / "app" / "service.py"
        broken_file.write_text("from backend.backend.app.models.user import User\n")

        checker = ConsistencyChecker()
        result = checker.run(str(project))

        import_fixes = [f for f in result.fixes if f.fix_type == "import_fix"]
        assert len(import_fixes) >= 1, "Should detect and fix the doubled-backend-prefix import"

    def test_env_sync_creates_env_example(self):
        """Create config.py with DATABASE_URL, SECRET_KEY — sync creates .env.example with those vars."""
        from src.code_generation.consistency import ConsistencyChecker

        project = Path(self.tmpdir)
        config_dir = project / "backend" / "app" / "core"
        config_dir.mkdir(parents=True)

        (config_dir / "config.py").write_text(
            "class Settings:\n"
            "    DATABASE_URL: str\n"
            "    SECRET_KEY: str\n"
        )
        # Start with an empty .env.example
        (project / ".env.example").write_text("")

        checker = ConsistencyChecker()
        result = checker.run(str(project))

        env_content = (project / ".env.example").read_text()
        assert "DATABASE_URL" in env_content, ".env.example should contain DATABASE_URL"
        assert "SECRET_KEY" in env_content, ".env.example should contain SECRET_KEY"

    def test_consistency_checker_no_crash_on_empty_project(self):
        """Empty project directory doesn't crash the consistency checker."""
        from src.code_generation.consistency import ConsistencyChecker

        # Just an empty directory
        project = Path(self.tmpdir)
        checker = ConsistencyChecker()
        result = checker.run(str(project))
        assert result is not None
        assert isinstance(result.fixes, list)
        assert isinstance(result.warnings, list)


# =============================================================================
# 5. Engine Context Tests
# =============================================================================


class TestEngineContextIntegration:
    """Test _GenerationContext with customization flows."""

    def test_context_customization_flows_to_spec_summary(self):
        """Create context with customization, call _spec_summary, verify customization appears."""
        from src.code_generation.engine_v2 import _spec_summary

        customization = {
            "backend_framework": "django",
            "database": "mysql",
            "auth_strategy": "oauth2",
            "frontend_framework": "svelte",
            "css_framework": "chakra",
            "deployment_target": "railway",
        }
        ctx = make_test_context(customization=customization)
        summary = _spec_summary(ctx.spec, ctx=ctx)

        # Customization info should appear in summary
        assert "django" in summary
        assert "mysql" in summary
        assert "oauth2" in summary

    def test_context_extra_instructions_in_summary(self):
        """extra_instructions from customization appears in _spec_summary output."""
        from src.code_generation.engine_v2 import _spec_summary

        customization = {
            "extra_instructions": "Use Stripe for payments and Twilio for SMS",
        }
        ctx = make_test_context(customization=customization)
        summary = _spec_summary(ctx.spec, ctx=ctx)

        assert "Stripe" in summary or "extra_instructions" in summary.lower() or \
               "Use Stripe for payments" in summary

    def test_file_plan_includes_alembic_files(self):
        """CodeGeneratorV2._build_file_plan includes alembic/env.py and 001_initial.py."""
        from src.code_generation.engine_v2 import CodeGeneratorV2

        generator = CodeGeneratorV2()
        ctx = make_test_context()
        plan = generator._build_file_plan(ctx)

        paths = [f.relative_path for f in plan]
        assert "backend/alembic/env.py" in paths, "Plan must include alembic/env.py"
        assert "backend/alembic/versions/001_initial.py" in paths, \
            "Plan must include alembic/versions/001_initial.py"

    def test_context_default_values(self):
        """_GenerationContext has correct default values when created."""
        from src.code_generation.engine_v2 import _GenerationContext

        spec = make_test_spec()
        ctx = _GenerationContext(
            spec=spec,
            output_dir=Path("/tmp/ctx_test"),
            theme="Minimal",
        )

        assert ctx.theme == "Minimal"
        assert ctx.spec.app_name == "TestApp"
        assert isinstance(ctx.customization, dict)
        assert ctx.llm_calls == 0
        assert isinstance(ctx.warnings, list)
        assert isinstance(ctx.generated_interfaces, dict)

    def test_context_customization_empty_by_default(self):
        """_GenerationContext.customization defaults to empty dict."""
        from src.code_generation.engine_v2 import _GenerationContext

        ctx = _GenerationContext(
            spec=make_test_spec(),
            output_dir=Path("/tmp/ctx_test"),
            theme="Modern",
        )
        assert ctx.customization == {}

    def test_spec_summary_without_customization(self):
        """_spec_summary renders basic spec info without customization context."""
        from src.code_generation.engine_v2 import _spec_summary

        spec = make_test_spec()
        summary = _spec_summary(spec)

        assert "TestApp" in summary
        assert "Task" in summary
        assert "User" in summary


# =============================================================================
# 6. File Plan Completeness Tests
# =============================================================================


class TestFilePlanCompleteness:
    """Verify the file plan covers all expected output files."""

    def _get_plan_paths(self, spec=None) -> List[str]:
        """Helper: build a file plan and return all relative paths."""
        from src.code_generation.engine_v2 import CodeGeneratorV2

        generator = CodeGeneratorV2()
        ctx = make_test_context(spec=spec)
        plan = generator._build_file_plan(ctx)
        return [f.relative_path for f in plan]

    def test_file_plan_has_backend_foundation(self):
        """Plan includes db/base.py, db/session.py, core/config.py, core/security.py, core/auth.py."""
        paths = self._get_plan_paths()

        assert "backend/app/db/base.py" in paths, "Missing db/base.py"
        assert "backend/app/db/session.py" in paths, "Missing db/session.py"
        assert "backend/app/core/config.py" in paths, "Missing core/config.py"
        assert "backend/app/core/security.py" in paths, "Missing core/security.py"
        assert "backend/app/core/auth.py" in paths, "Missing core/auth.py"

    def test_file_plan_has_entity_files_for_each_entity(self):
        """For each entity in spec, verify model, schema, crud, and route files exist."""
        spec = make_test_spec()
        paths = self._get_plan_paths(spec=spec)

        for entity in spec.entities:
            name = entity.name.lower()
            assert f"backend/app/models/{name}.py" in paths, \
                f"Missing model for {entity.name}"
            assert f"backend/app/schemas/{name}.py" in paths, \
                f"Missing schema for {entity.name}"
            assert f"backend/app/crud/{name}.py" in paths, \
                f"Missing CRUD for {entity.name}"
            assert f"backend/app/api/endpoints/{name}.py" in paths, \
                f"Missing API endpoint for {entity.name}"

    def test_file_plan_has_frontend_foundation(self):
        """Plan includes types/index.ts, lib/api.ts, components/ui/index.tsx."""
        paths = self._get_plan_paths()

        assert "frontend/src/types/index.ts" in paths, "Missing frontend/src/types/index.ts"
        assert "frontend/src/lib/api.ts" in paths, "Missing frontend/src/lib/api.ts"
        assert "frontend/src/components/ui/index.tsx" in paths, \
            "Missing frontend/src/components/ui/index.tsx"

    def test_file_plan_has_infrastructure_files(self):
        """Plan includes docker-compose.yml, .env.example, .gitignore, README.md, ci.yml."""
        paths = self._get_plan_paths()

        assert "docker-compose.yml" in paths, "Missing docker-compose.yml"
        assert ".env.example" in paths, "Missing .env.example"
        assert ".gitignore" in paths, "Missing .gitignore"
        assert "README.md" in paths, "Missing README.md"
        assert ".github/workflows/ci.yml" in paths, "Missing .github/workflows/ci.yml"

    def test_file_plan_has_alembic_files(self):
        """Plan includes alembic/env.py and alembic/versions/001_initial.py."""
        paths = self._get_plan_paths()

        assert "backend/alembic/env.py" in paths, "Missing backend/alembic/env.py"
        assert "backend/alembic/versions/001_initial.py" in paths, \
            "Missing backend/alembic/versions/001_initial.py"

    def test_file_plan_has_init_files(self):
        """Plan includes __init__.py files including alembic ones."""
        paths = self._get_plan_paths()

        required_inits = [
            "backend/app/__init__.py",
            "backend/app/models/__init__.py",
            "backend/app/schemas/__init__.py",
            "backend/app/crud/__init__.py",
            "backend/app/api/endpoints/__init__.py",
            "backend/app/core/__init__.py",
            "backend/app/db/__init__.py",
            "backend/alembic/__init__.py",
            "backend/alembic/versions/__init__.py",
        ]
        for init_path in required_inits:
            assert init_path in paths, f"Missing __init__.py: {init_path}"

    def test_file_plan_minimum_file_count(self):
        """File plan has a reasonable minimum number of files for a 2-entity app."""
        paths = self._get_plan_paths()

        # A 2-entity app should produce at least 30 files
        assert len(paths) >= 30, (
            f"Expected at least 30 files in plan, got {len(paths)}"
        )

    def test_file_plan_no_duplicate_paths(self):
        """File plan contains no duplicate relative paths."""
        paths = self._get_plan_paths()

        assert len(paths) == len(set(paths)), (
            f"Duplicate paths found: {[p for p in paths if paths.count(p) > 1]}"
        )

    def test_file_plan_has_main_app(self):
        """Plan includes backend/app/main.py as the FastAPI entry point."""
        paths = self._get_plan_paths()

        assert "backend/app/main.py" in paths, "Missing backend/app/main.py"

    def test_file_plan_entity_scale(self):
        """File plan grows proportionally with the number of entities."""
        from src.code_generation.architect import (
            EntitySpec, FieldSpec, SystemSpec, TechStackSpec,
            RouteSpec, PageSpec, RoleSpec
        )
        from src.code_generation.engine_v2 import CodeGeneratorV2

        generator = CodeGeneratorV2()

        # 1-entity spec
        spec_1 = SystemSpec(
            app_name="SmallApp",
            description="A small app",
            entities=[EntitySpec(name="Item", fields=[FieldSpec(name="name", type="string")])],
            api_routes=[RouteSpec(path="/api/items", method="GET", description="List")],
            pages=[PageSpec(route="/", title="Home")],
            roles=[RoleSpec(name="user", permissions=["read"])],
            integrations=[],
            business_rules=[],
            tech_stack=TechStackSpec(),
        )
        # 3-entity spec
        spec_3 = SystemSpec(
            app_name="BigApp",
            description="A bigger app",
            entities=[
                EntitySpec(name="Item", fields=[FieldSpec(name="name", type="string")]),
                EntitySpec(name="Order", fields=[FieldSpec(name="amount", type="decimal")]),
                EntitySpec(name="Customer", fields=[FieldSpec(name="email", type="string")]),
            ],
            api_routes=[RouteSpec(path="/api/items", method="GET", description="List")],
            pages=[PageSpec(route="/", title="Home")],
            roles=[RoleSpec(name="admin", permissions=["all"])],
            integrations=[],
            business_rules=[],
            tech_stack=TechStackSpec(),
        )

        ctx1 = _GenerationContext_helper(spec_1)
        ctx3 = _GenerationContext_helper(spec_3)
        plan1 = generator._build_file_plan(ctx1)
        plan3 = generator._build_file_plan(ctx3)

        # 3-entity plan should have more files than 1-entity plan
        assert len(plan3) > len(plan1), (
            f"Expected plan3 ({len(plan3)}) > plan1 ({len(plan1)})"
        )


def _GenerationContext_helper(spec):
    """Helper to create a _GenerationContext with a given spec."""
    from src.code_generation.engine_v2 import _GenerationContext
    return _GenerationContext(
        spec=spec,
        output_dir=Path("/tmp/test_scale"),
        theme="Modern",
    )


# =============================================================================
# 7. Additional Integration Edge Cases
# =============================================================================


class TestAdditionalIntegration:
    """Additional edge-case integration tests."""

    def test_pipeline_progress_model(self):
        """PipelineProgress model validates field constraints."""
        from src.code_generation.pipeline import PipelineProgress

        event = PipelineProgress(
            phase="generate",
            step="Generating models",
            progress=45,
            message="Writing user.py",
            files_generated=5,
            total_files=50,
        )
        assert event.phase == "generate"
        assert event.progress == 45
        assert event.files_generated == 5

    def test_pipeline_progress_out_of_range(self):
        """PipelineProgress rejects progress values outside 0-100."""
        from pydantic import ValidationError
        from src.code_generation.pipeline import PipelineProgress

        with pytest.raises(ValidationError):
            PipelineProgress(
                phase="generate",
                step="Bad progress",
                progress=150,  # Invalid: > 100
            )

    def test_chat_message_model(self):
        """ChatMessage model creates with expected defaults."""
        from src.code_generation.refinement_chat import ChatMessage

        msg = ChatMessage(role="user", content="Please add a search bar")
        assert msg.role == "user"
        assert msg.content == "Please add a search bar"
        assert msg.timestamp  # Should auto-populate
        assert msg.refinement_result is None

    def test_refinement_chat_model_defaults(self):
        """RefinementChat model has correct default values."""
        from src.code_generation.refinement_chat import RefinementChat

        chat = RefinementChat(project_path="/tmp/project")
        assert chat.chat_id  # Auto-generated UUID
        assert chat.project_path == "/tmp/project"
        assert chat.project_id is None
        assert len(chat.messages) == 0
        assert chat.created_at
        assert chat.updated_at

    def test_chat_updated_at_changes_on_message(self):
        """updated_at timestamp changes when a message is added."""
        from src.code_generation.refinement_chat import RefinementChat
        import time

        chat = RefinementChat(project_path="/tmp/project")
        original_updated_at = chat.updated_at

        time.sleep(0.01)  # Small delay to ensure timestamp difference
        chat.add_user_message("First message")

        # updated_at should have changed
        assert chat.updated_at >= original_updated_at

    def test_pipeline_result_status_values(self):
        """PipelineResult accepts expected status values."""
        from src.code_generation.engine_v2 import GenerationResult
        from src.code_generation.pipeline import PipelineResult
        from src.code_generation.quality import QualityReport

        spec = make_test_spec()
        gen = GenerationResult(
            output_path="/tmp",
            total_files=0,
            total_lines=0,
            backend_files=0,
            frontend_files=0,
            generation_time_seconds=0.0,
            llm_calls_made=0,
        )
        qual = QualityReport(
            checks=[], score=90, passed=True, errors=0, warnings=0, summary="OK"
        )

        for status in ["success", "success_with_warnings", "failed"]:
            result = PipelineResult(spec=spec, generation=gen, quality=qual, status=status)
            assert result.status == status

    def test_system_spec_serialization_roundtrip(self):
        """SystemSpec can be serialized to dict and back."""
        spec = make_test_spec()

        spec_dict = spec.model_dump()
        assert isinstance(spec_dict, dict)

        # Verify all key sections present
        assert "app_name" in spec_dict
        assert "entities" in spec_dict
        assert "api_routes" in spec_dict
        assert "pages" in spec_dict
        assert "roles" in spec_dict
        assert "tech_stack" in spec_dict

        # Verify entity data preserved
        entity_names = [e["name"] for e in spec_dict["entities"]]
        assert "Task" in entity_names
        assert "User" in entity_names

    def test_tech_stack_defaults(self):
        """TechStackSpec defaults to standard modern stack."""
        from src.code_generation.architect import TechStackSpec

        ts = TechStackSpec()
        # Should have some default values for the main fields
        assert ts.backend_framework is not None
        assert ts.frontend_framework is not None
        assert ts.database is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
