"""
Tests for Ignara Code Generation v2 improvements.

Covers: ConsistencyChecker, customization options, refinement chat,
pipeline integration, and engine_v2 enhancements.
"""
import asyncio
import os
import shutil
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


def run_async(coro):
    """Helper to run async code in tests."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# =============================================================================
# 1. ConsistencyChecker Tests
# =============================================================================


class TestConsistencyCheckerEnsureInitFiles:
    """Tests for ConsistencyChecker._ensure_init_files()."""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()

    def teardown_method(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _make_project(self, structure: dict) -> Path:
        """Create a project structure from a dict of path->content."""
        root = Path(self.tmpdir)
        for rel_path, content in structure.items():
            full = root / rel_path
            full.parent.mkdir(parents=True, exist_ok=True)
            full.write_text(content)
        return root

    def test_creates_missing_init_in_backend(self):
        """Missing __init__.py is created in a backend package with .py files."""
        from src.code_generation.consistency import ConsistencyChecker

        project = self._make_project({
            "backend/app/models/user.py": "class User: pass",
        })
        checker = ConsistencyChecker()
        result = checker.run(str(project))

        # __init__.py should have been created in backend/app/models/
        init_path = project / "backend" / "app" / "models" / "__init__.py"
        assert init_path.exists(), "Missing __init__.py should be created"

    def test_does_not_duplicate_existing_init(self):
        """Existing __init__.py is not touched."""
        from src.code_generation.consistency import ConsistencyChecker

        project = self._make_project({
            "backend/app/models/__init__.py": "# existing",
            "backend/app/models/user.py": "class User: pass",
        })
        checker = ConsistencyChecker()
        result = checker.run(str(project))

        # Verify the existing init was not re-created (content unchanged)
        content = (project / "backend" / "app" / "models" / "__init__.py").read_text()
        assert content == "# existing", "Existing __init__.py must not be overwritten"

    def test_no_init_for_empty_dirs(self):
        """Directories without .py files do not get __init__.py."""
        from src.code_generation.consistency import ConsistencyChecker

        project = self._make_project({
            "backend/app/static/logo.png": "",
        })
        checker = ConsistencyChecker()
        result = checker.run(str(project))

        init_path = project / "backend" / "app" / "static" / "__init__.py"
        assert not init_path.exists(), "__init__.py should NOT be created in a non-Python dir"

    def test_init_fix_type_is_init_created(self):
        """The fix recorded uses fix_type='init_created'."""
        from src.code_generation.consistency import ConsistencyChecker

        project = self._make_project({
            "backend/app/core/config.py": "class Settings: pass",
        })
        checker = ConsistencyChecker()
        result = checker.run(str(project))

        init_fixes = [f for f in result.fixes if f.fix_type == "init_created"]
        assert len(init_fixes) >= 1, "At least one init_created fix should be recorded"

    def test_nonexistent_project_dir_returns_warning(self):
        """Running on a non-existent directory returns a warning, not an exception."""
        from src.code_generation.consistency import ConsistencyChecker

        checker = ConsistencyChecker()
        result = checker.run("/this/path/does/not/exist")

        assert len(result.warnings) >= 1
        assert "not found" in result.warnings[0].lower()


class TestConsistencyCheckerFixPythonImports:
    """Tests for ConsistencyChecker._fix_python_imports() — app.xxx → backend.app.xxx."""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()

    def teardown_method(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_fixes_doubled_backend_prefix_import(self):
        """'from backend.backend.utils.helper import foo' → 'from backend.utils.helper import foo'."""
        from src.code_generation.consistency import ConsistencyChecker

        project = Path(self.tmpdir)
        # Create the real module at backend/utils/helper.py
        (project / "backend" / "utils").mkdir(parents=True)
        (project / "backend" / "utils" / "__init__.py").write_text("")
        (project / "backend" / "utils" / "helper.py").write_text("def foo(): pass")
        (project / "backend" / "__init__.py").write_text("")

        # Create a file that doubles the 'backend.' prefix — a common LLM mistake
        broken_file = project / "backend" / "service.py"
        broken_file.write_text("from backend.backend.utils.helper import foo\n")

        checker = ConsistencyChecker()
        result = checker.run(str(project))

        import_fixes = [f for f in result.fixes if f.fix_type == "import_fix"]
        assert len(import_fixes) >= 1, "Should detect and fix the doubled-backend-prefix import"
        assert any("backend.utils.helper" in f.description for f in import_fixes)

    def test_skips_external_imports(self):
        """External imports (fastapi, pydantic, etc.) are not flagged as broken."""
        from src.code_generation.consistency import ConsistencyChecker

        project = Path(self.tmpdir)
        (project / "backend" / "app").mkdir(parents=True)
        (project / "backend" / "app" / "main.py").write_text(
            "from fastapi import FastAPI\nfrom pydantic import BaseModel\n"
        )

        checker = ConsistencyChecker()
        result = checker.run(str(project))

        import_fixes = [f for f in result.fixes if f.fix_type == "import_fix"]
        assert len(import_fixes) == 0, "External stdlib/third-party imports should not trigger fixes"

    def test_skips_syntax_error_files(self):
        """Files with syntax errors are gracefully skipped."""
        from src.code_generation.consistency import ConsistencyChecker

        project = Path(self.tmpdir)
        (project / "backend" / "app").mkdir(parents=True)
        bad_file = project / "backend" / "app" / "broken.py"
        bad_file.write_text("def foo(: !!!\n  invalid python code !!!!")

        # Should not raise any exception
        checker = ConsistencyChecker()
        result = checker.run(str(project))
        assert isinstance(result.fixes, list)


class TestIsExternalImport:
    """Tests for ConsistencyChecker._is_external_import()."""

    def test_stdlib_modules_are_external(self):
        """Standard library modules are identified as external."""
        from src.code_generation.consistency import ConsistencyChecker

        for module in ["os", "sys", "json", "pathlib", "asyncio", "typing", "logging", "re"]:
            assert ConsistencyChecker._is_external_import(module), f"{module} should be external"

    def test_fastapi_project_deps_are_external(self):
        """Common FastAPI project dependencies are identified as external."""
        from src.code_generation.consistency import ConsistencyChecker

        for module in ["fastapi", "pydantic", "sqlalchemy", "jose", "passlib", "httpx", "redis"]:
            assert ConsistencyChecker._is_external_import(module), f"{module} should be external"

    def test_dotted_external_modules_are_external(self):
        """Dotted paths like 'fastapi.routing' are identified as external."""
        from src.code_generation.consistency import ConsistencyChecker

        assert ConsistencyChecker._is_external_import("fastapi.routing")
        assert ConsistencyChecker._is_external_import("sqlalchemy.orm")
        assert ConsistencyChecker._is_external_import("pydantic.fields")

    def test_project_modules_are_not_external(self):
        """Internal project module paths are not marked as external."""
        from src.code_generation.consistency import ConsistencyChecker

        assert not ConsistencyChecker._is_external_import("app.models.user")
        assert not ConsistencyChecker._is_external_import("backend.app.core.config")
        assert not ConsistencyChecker._is_external_import("myproject.utils")


class TestConsistencyCheckerSyncEnvVars:
    """Tests for ConsistencyChecker._sync_env_vars()."""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()

    def teardown_method(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_adds_missing_vars_to_env_example(self):
        """Env vars in config.py but missing from .env.example are added."""
        from src.code_generation.consistency import ConsistencyChecker

        project = Path(self.tmpdir)
        config_dir = project / "backend" / "app" / "core"
        config_dir.mkdir(parents=True)

        (config_dir / "config.py").write_text(
            "class Settings(BaseSettings):\n"
            "    DATABASE_URL: str\n"
            "    SECRET_KEY: str\n"
            "    REDIS_URL: str\n"
        )
        (project / ".env.example").write_text("DATABASE_URL=postgresql://localhost/db\n")

        checker = ConsistencyChecker()
        result = checker.run(str(project))

        env_content = (project / ".env.example").read_text()
        assert "SECRET_KEY" in env_content, "SECRET_KEY should be added to .env.example"
        assert "REDIS_URL" in env_content, "REDIS_URL should be added to .env.example"

    def test_does_not_duplicate_existing_vars(self):
        """Vars already in .env.example are not duplicated."""
        from src.code_generation.consistency import ConsistencyChecker

        project = Path(self.tmpdir)
        config_dir = project / "backend" / "app" / "core"
        config_dir.mkdir(parents=True)

        (config_dir / "config.py").write_text(
            "class Settings:\n"
            "    DATABASE_URL: str\n"
        )
        (project / ".env.example").write_text("DATABASE_URL=postgresql://localhost/db\n")

        checker = ConsistencyChecker()
        result = checker.run(str(project))

        env_content = (project / ".env.example").read_text()
        occurrences = env_content.count("DATABASE_URL")
        assert occurrences == 1, "DATABASE_URL should appear only once"

    def test_uses_sensible_placeholder_for_secrets(self):
        """SECRET_KEY gets a 'change-me-in-production' placeholder."""
        from src.code_generation.consistency import ConsistencyChecker

        project = Path(self.tmpdir)
        config_dir = project / "backend" / "app" / "core"
        config_dir.mkdir(parents=True)

        (config_dir / "config.py").write_text(
            "class Settings:\n"
            "    SECRET_KEY: str\n"
        )
        (project / ".env.example").write_text("")

        checker = ConsistencyChecker()
        result = checker.run(str(project))

        env_content = (project / ".env.example").read_text()
        assert "change-me-in-production" in env_content

    def test_env_sync_fix_type_recorded(self):
        """An env_sync fix is recorded when vars are added."""
        from src.code_generation.consistency import ConsistencyChecker

        project = Path(self.tmpdir)
        config_dir = project / "backend" / "app" / "core"
        config_dir.mkdir(parents=True)

        (config_dir / "config.py").write_text(
            "class Settings:\n"
            "    NEW_FEATURE_FLAG: str\n"
        )
        (project / ".env.example").write_text("")

        checker = ConsistencyChecker()
        result = checker.run(str(project))

        env_fixes = [f for f in result.fixes if f.fix_type == "env_sync"]
        assert len(env_fixes) == 1


class TestConsistencyCheckerFrontendImports:
    """Tests for ConsistencyChecker._fix_frontend_imports()."""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()

    def teardown_method(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_warns_about_missing_at_alias_import(self):
        """A TypeScript file importing a non-existent @/ path generates a warning."""
        from src.code_generation.consistency import ConsistencyChecker

        project = Path(self.tmpdir)
        src_dir = project / "frontend" / "src" / "components"
        src_dir.mkdir(parents=True)

        # File that imports something that doesn't exist
        (src_dir / "MyComponent.tsx").write_text(
            'import { Button } from "@/components/ui/button";\n'
        )

        checker = ConsistencyChecker()
        result = checker.run(str(project))

        # The missing import should produce a warning
        matching_warnings = [w for w in result.warnings if "@/components/ui/button" in w]
        assert len(matching_warnings) >= 1, "Missing @/ import should produce a warning"

    def test_no_warning_for_resolvable_import(self):
        """An import that resolves via the available module map produces no warning."""
        from src.code_generation.consistency import ConsistencyChecker

        project = Path(self.tmpdir)
        src_dir = project / "frontend" / "src"
        (src_dir / "components" / "ui").mkdir(parents=True)

        # The actual module exists
        (src_dir / "components" / "ui" / "button.tsx").write_text(
            "export const Button = () => null;"
        )
        # A file that correctly imports it
        (src_dir / "components" / "MyComponent.tsx").write_text(
            'import { Button } from "@/components/ui/button";\n'
        )

        checker = ConsistencyChecker()
        result = checker.run(str(project))

        matching_warnings = [w for w in result.warnings if "@/components/ui/button" in w]
        assert len(matching_warnings) == 0, "Resolvable import should not produce a warning"

    def test_no_frontend_check_without_frontend_dir(self):
        """If there's no frontend/ dir, the frontend check is silently skipped."""
        from src.code_generation.consistency import ConsistencyChecker

        project = Path(self.tmpdir)
        (project / "backend").mkdir()

        checker = ConsistencyChecker()
        result = checker.run(str(project))
        # No warnings should be about frontend imports
        frontend_warnings = [w for w in result.warnings if "@/" in w]
        assert len(frontend_warnings) == 0


class TestConsistencyCheckerRunMethod:
    """Integration test for the full ConsistencyChecker.run() method."""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()

    def teardown_method(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_run_returns_consistency_result(self):
        """run() always returns a ConsistencyResult object."""
        from src.code_generation.consistency import ConsistencyChecker, ConsistencyResult

        project = Path(self.tmpdir)
        (project / "backend" / "app").mkdir(parents=True)
        (project / "backend" / "app" / "main.py").write_text("app = None")

        checker = ConsistencyChecker()
        result = checker.run(str(project))

        assert isinstance(result, ConsistencyResult)
        assert hasattr(result, "fixes")
        assert hasattr(result, "warnings")
        assert hasattr(result, "total_fixes")

    def test_total_fixes_matches_fix_list_length(self):
        """total_fixes property equals len(fixes)."""
        from src.code_generation.consistency import ConsistencyChecker

        project = Path(self.tmpdir)
        config_dir = project / "backend" / "app" / "core"
        config_dir.mkdir(parents=True)
        (config_dir / "config.py").write_text(
            "class Settings:\n    NEW_VAR: str\n"
        )
        (project / ".env.example").write_text("")

        checker = ConsistencyChecker()
        result = checker.run(str(project))

        assert result.total_fixes == len(result.fixes)

    def test_consistency_fix_repr(self):
        """ConsistencyFix __repr__ works correctly."""
        from src.code_generation.consistency import ConsistencyFix

        fix = ConsistencyFix(
            file_path="backend/app/__init__.py",
            description="Created missing __init__.py for Python package",
            fix_type="init_created",
        )
        r = repr(fix)
        assert "init_created" in r
        assert "backend/app/__init__.py" in r


# =============================================================================
# 2. GenerateRequest Customization Fields
# =============================================================================


class TestGenerateRequestCustomization:
    """Tests for GenerateRequest customization fields in routes.py."""

    def test_generate_request_default_values(self):
        """GenerateRequest applies correct defaults for all customization fields."""
        from src.code_generation.routes import GenerateRequest

        req = GenerateRequest(
            idea_name="TestApp",
            description="A test application for testing purposes",
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

    def test_generate_request_custom_values(self):
        """GenerateRequest accepts non-default customization values."""
        from src.code_generation.routes import GenerateRequest

        req = GenerateRequest(
            idea_name="ExpressApp",
            description="A Node application using Express and MongoDB",
            backend_framework="express",
            database="mongodb",
            auth_strategy="session",
            frontend_framework="react-vite",
            css_framework="material-ui",
            deployment_target="vercel",
            include_tests=False,
            include_ci=False,
            api_style="graphql",
            extra_instructions="Use TypeScript everywhere",
        )
        assert req.backend_framework == "express"
        assert req.database == "mongodb"
        assert req.auth_strategy == "session"
        assert req.frontend_framework == "react-vite"
        assert req.css_framework == "material-ui"
        assert req.deployment_target == "vercel"
        assert req.include_tests is False
        assert req.include_ci is False
        assert req.api_style == "graphql"
        assert req.extra_instructions == "Use TypeScript everywhere"

    def test_extra_instructions_max_length_validation(self):
        """extra_instructions raises ValidationError when it exceeds 2000 chars."""
        from pydantic import ValidationError
        from src.code_generation.routes import GenerateRequest

        with pytest.raises(ValidationError):
            GenerateRequest(
                idea_name="Test",
                description="A valid description here",
                extra_instructions="x" * 2001,  # exceeds max_length=2000
            )

    def test_idea_name_min_length(self):
        """idea_name must have at least 1 character."""
        from pydantic import ValidationError
        from src.code_generation.routes import GenerateRequest

        with pytest.raises(ValidationError):
            GenerateRequest(
                idea_name="",
                description="A valid description here",
            )

    def test_description_min_length(self):
        """description must have at least 10 characters."""
        from pydantic import ValidationError
        from src.code_generation.routes import GenerateRequest

        with pytest.raises(ValidationError):
            GenerateRequest(
                idea_name="Test",
                description="Short",  # less than 10 chars
            )

    def test_max_fix_rounds_bounds(self):
        """max_fix_rounds must be between 0 and 5."""
        from pydantic import ValidationError
        from src.code_generation.routes import GenerateRequest

        # Valid boundary values
        req_min = GenerateRequest(
            idea_name="Test", description="A test application here", max_fix_rounds=0
        )
        req_max = GenerateRequest(
            idea_name="Test", description="A test application here", max_fix_rounds=5
        )
        assert req_min.max_fix_rounds == 0
        assert req_max.max_fix_rounds == 5

        # Out of bounds
        with pytest.raises(ValidationError):
            GenerateRequest(
                idea_name="Test", description="A test application here", max_fix_rounds=6
            )

    def test_generate_request_optional_features(self):
        """features field defaults to None and accepts a list of strings."""
        from src.code_generation.routes import GenerateRequest

        req_no_features = GenerateRequest(
            idea_name="App", description="A simple test application"
        )
        assert req_no_features.features is None

        req_with_features = GenerateRequest(
            idea_name="App",
            description="A simple test application",
            features=["auth", "dashboard", "api"],
        )
        assert req_with_features.features == ["auth", "dashboard", "api"]


# =============================================================================
# 3. Pipeline Consistency Integration
# =============================================================================


class TestPipelineResultFields:
    """Tests for PipelineResult model fields added in this session."""

    def _make_pipeline_result(self, **kwargs):
        """Helper to build a valid PipelineResult using real model instances."""
        from src.code_generation.pipeline import PipelineResult
        from src.code_generation.architect import SystemSpec, TechStackSpec
        from src.code_generation.engine_v2 import GenerationResult
        from src.code_generation.quality import QualityReport

        spec = SystemSpec(
            app_name="Test",
            description="Test",
            entities=[],
            api_routes=[],
            pages=[],
            roles=[],
            integrations=[],
            business_rules=[],
            tech_stack=TechStackSpec(),
        )
        gen_result = GenerationResult(output_path="/tmp/test")
        quality = QualityReport()
        return PipelineResult(spec=spec, generation=gen_result, quality=quality, **kwargs)

    def test_pipeline_result_has_consistency_fixes_field(self):
        """PipelineResult.consistency_fixes field exists and defaults to 0."""
        result = self._make_pipeline_result()

        assert hasattr(result, "consistency_fixes")
        assert result.consistency_fixes == 0

    def test_pipeline_result_has_customization_field(self):
        """PipelineResult.customization field exists and defaults to None."""
        result = self._make_pipeline_result()

        assert hasattr(result, "customization")
        assert result.customization is None

    def test_pipeline_result_customization_can_be_set(self):
        """PipelineResult.customization accepts a dict."""
        custom = {"backend_framework": "django", "database": "sqlite"}
        result = self._make_pipeline_result(customization=custom)

        assert result.customization == custom

    def test_generation_pipeline_has_consistency_attribute(self):
        """GenerationPipeline exposes a .consistency attribute of the right type."""
        from src.code_generation.pipeline import GenerationPipeline
        from src.code_generation.consistency import ConsistencyChecker

        pipeline = GenerationPipeline()

        assert hasattr(pipeline, "consistency")
        assert isinstance(pipeline.consistency, ConsistencyChecker)

    def test_pipeline_progress_model_fields(self):
        """PipelineProgress model accepts all documented fields."""
        from src.code_generation.pipeline import PipelineProgress

        event = PipelineProgress(
            phase="generate",
            step="backend",
            progress=42,
            message="Generating backend files",
            files_generated=10,
            total_files=50,
        )
        assert event.phase == "generate"
        assert event.step == "backend"
        assert event.progress == 42
        assert event.files_generated == 10


# =============================================================================
# 4. RefinementChat Tests
# =============================================================================


class TestChatMessage:
    """Tests for the ChatMessage model."""

    def test_chat_message_creation_user(self):
        """ChatMessage can be created with role='user'."""
        from src.code_generation.refinement_chat import ChatMessage

        msg = ChatMessage(role="user", content="Add a dark mode toggle")
        assert msg.role == "user"
        assert msg.content == "Add a dark mode toggle"
        assert msg.timestamp is not None
        assert msg.refinement_result is None

    def test_chat_message_creation_assistant(self):
        """ChatMessage can be created with role='assistant'."""
        from src.code_generation.refinement_chat import ChatMessage

        msg = ChatMessage(role="assistant", content="I've added dark mode support")
        assert msg.role == "assistant"
        assert msg.content == "I've added dark mode support"

    def test_chat_message_with_refinement_result(self):
        """ChatMessage stores refinement_result dict."""
        from src.code_generation.refinement_chat import ChatMessage

        result_dict = {
            "files_modified": [{"path": "frontend/src/app/globals.css"}],
            "files_created": [],
            "explanation": "Added dark mode CSS variables",
        }
        msg = ChatMessage(
            role="assistant",
            content="Done!",
            refinement_result=result_dict,
        )
        assert msg.refinement_result == result_dict
        assert msg.refinement_result["files_modified"][0]["path"] == "frontend/src/app/globals.css"

    def test_chat_message_timestamp_is_set_automatically(self):
        """ChatMessage timestamp is auto-populated."""
        from src.code_generation.refinement_chat import ChatMessage

        msg = ChatMessage(role="user", content="Hello")
        assert msg.timestamp != ""
        assert "T" in msg.timestamp  # ISO 8601 format


class TestRefinementChat:
    """Tests for RefinementChat conversation management."""

    def test_add_user_message(self):
        """add_user_message appends a user message and returns it."""
        from src.code_generation.refinement_chat import RefinementChat

        chat = RefinementChat(project_path="/tmp/myproject")
        msg = chat.add_user_message("Add a search feature")

        assert msg.role == "user"
        assert msg.content == "Add a search feature"
        assert len(chat.messages) == 1
        assert chat.messages[0] is msg

    def test_add_assistant_message(self):
        """add_assistant_message appends an assistant message."""
        from src.code_generation.refinement_chat import RefinementChat

        chat = RefinementChat(project_path="/tmp/myproject")
        msg = chat.add_assistant_message("I'll add search functionality")

        assert msg.role == "assistant"
        assert len(chat.messages) == 1

    def test_add_assistant_message_with_result(self):
        """add_assistant_message stores refinement_result on the message."""
        from src.code_generation.refinement_chat import RefinementChat

        chat = RefinementChat(project_path="/tmp/myproject")
        result = {"files_modified": [{"path": "search.py"}], "explanation": "Added search"}
        msg = chat.add_assistant_message("Done!", refinement_result=result)

        assert msg.refinement_result == result

    def test_updated_at_changes_on_message(self):
        """updated_at is refreshed every time a message is added."""
        import time
        from src.code_generation.refinement_chat import RefinementChat

        chat = RefinementChat(project_path="/tmp/project")
        original_updated_at = chat.updated_at
        time.sleep(0.01)  # ensure timestamp differs
        chat.add_user_message("Hello")
        assert chat.updated_at >= original_updated_at

    def test_get_context_summary_empty(self):
        """get_context_summary on an empty chat returns an empty string."""
        from src.code_generation.refinement_chat import RefinementChat

        chat = RefinementChat(project_path="/tmp/project")
        summary = chat.get_context_summary()
        assert summary == ""

    def test_get_context_summary_with_messages(self):
        """get_context_summary formats user and assistant messages correctly."""
        from src.code_generation.refinement_chat import RefinementChat

        chat = RefinementChat(project_path="/tmp/project")
        chat.add_user_message("Add dark mode")
        chat.add_assistant_message("I've added dark mode")

        summary = chat.get_context_summary()
        assert "User: Add dark mode" in summary
        assert "Assistant: I've added dark mode" in summary

    def test_get_context_summary_includes_changed_files(self):
        """get_context_summary includes changed files from refinement results."""
        from src.code_generation.refinement_chat import RefinementChat

        chat = RefinementChat(project_path="/tmp/project")
        chat.add_user_message("Update styles")
        chat.add_assistant_message(
            "Updated",
            refinement_result={
                "files_modified": [{"path": "globals.css"}, {"path": "theme.ts"}],
                "files_created": [],
            },
        )

        summary = chat.get_context_summary()
        assert "globals.css" in summary or "theme.ts" in summary

    def test_get_context_summary_respects_max_messages(self):
        """get_context_summary only returns the last max_messages messages."""
        from src.code_generation.refinement_chat import RefinementChat

        chat = RefinementChat(project_path="/tmp/project")
        for i in range(20):
            chat.add_user_message(f"Message {i}")

        summary = chat.get_context_summary(max_messages=3)
        # Only the last 3 messages should appear
        assert "Message 19" in summary
        assert "Message 18" in summary
        assert "Message 17" in summary
        assert "Message 0" not in summary

    def test_chat_id_is_auto_generated(self):
        """RefinementChat auto-generates a unique chat_id."""
        from src.code_generation.refinement_chat import RefinementChat

        chat1 = RefinementChat(project_path="/tmp/project1")
        chat2 = RefinementChat(project_path="/tmp/project2")
        assert chat1.chat_id != chat2.chat_id
        assert len(chat1.chat_id) > 0


class TestChatManager:
    """Tests for ChatManager session lifecycle."""

    def test_create_chat(self):
        """create_chat returns a new RefinementChat with the given project_path."""
        from src.code_generation.refinement_chat import ChatManager

        manager = ChatManager()
        chat = manager.create_chat(project_path="/tmp/myproject")

        assert chat.project_path == "/tmp/myproject"
        assert chat.chat_id is not None

    def test_get_chat_returns_existing_chat(self):
        """get_chat retrieves a previously created chat by ID."""
        from src.code_generation.refinement_chat import ChatManager

        manager = ChatManager()
        chat = manager.create_chat(project_path="/tmp/project")
        retrieved = manager.get_chat(chat.chat_id)

        assert retrieved is chat

    def test_get_chat_returns_none_for_unknown_id(self):
        """get_chat returns None for an unknown chat_id."""
        from src.code_generation.refinement_chat import ChatManager

        manager = ChatManager()
        result = manager.get_chat("nonexistent-id")
        assert result is None

    def test_list_chats_returns_all_chats(self):
        """list_chats returns all created chats."""
        from src.code_generation.refinement_chat import ChatManager

        manager = ChatManager()
        chat1 = manager.create_chat(project_path="/tmp/project1")
        chat2 = manager.create_chat(project_path="/tmp/project2")

        chats = manager.list_chats()
        assert len(chats) == 2
        chat_ids = {c.chat_id for c in chats}
        assert chat1.chat_id in chat_ids
        assert chat2.chat_id in chat_ids

    def test_list_chats_filters_by_project_path(self):
        """list_chats with project_path only returns matching chats."""
        from src.code_generation.refinement_chat import ChatManager

        manager = ChatManager()
        manager.create_chat(project_path="/tmp/project1")
        manager.create_chat(project_path="/tmp/project1")
        manager.create_chat(project_path="/tmp/project2")

        project1_chats = manager.list_chats(project_path="/tmp/project1")
        assert len(project1_chats) == 2
        for c in project1_chats:
            assert c.project_path == "/tmp/project1"

    def test_delete_chat_removes_it(self):
        """delete_chat removes the chat and returns True."""
        from src.code_generation.refinement_chat import ChatManager

        manager = ChatManager()
        chat = manager.create_chat(project_path="/tmp/project")
        result = manager.delete_chat(chat.chat_id)

        assert result is True
        assert manager.get_chat(chat.chat_id) is None

    def test_delete_chat_returns_false_for_unknown_id(self):
        """delete_chat returns False for an unknown chat_id."""
        from src.code_generation.refinement_chat import ChatManager

        manager = ChatManager()
        result = manager.delete_chat("nonexistent-id")
        assert result is False

    def test_send_message_raises_value_error_for_unknown_chat(self):
        """send_message raises ValueError when chat_id does not exist."""
        from src.code_generation.refinement_chat import ChatManager

        manager = ChatManager()

        with pytest.raises(ValueError, match="not found"):
            run_async(manager.send_message(chat_id="bad-id", instruction="Do something"))

    def test_create_chat_with_project_id(self):
        """create_chat accepts an optional project_id."""
        from src.code_generation.refinement_chat import ChatManager

        manager = ChatManager()
        chat = manager.create_chat(project_path="/tmp/project", project_id="proj-123")
        assert chat.project_id == "proj-123"

    def test_list_chats_sorted_by_updated_at_desc(self):
        """list_chats returns chats sorted by updated_at (most recent first)."""
        import time
        from src.code_generation.refinement_chat import ChatManager

        manager = ChatManager()
        chat1 = manager.create_chat(project_path="/tmp/p1")
        time.sleep(0.01)
        chat2 = manager.create_chat(project_path="/tmp/p2")
        time.sleep(0.01)
        # Add a message to chat1 to bump its updated_at
        chat1.add_user_message("bump")

        chats = manager.list_chats()
        # chat1 should come first (most recently updated)
        assert chats[0].chat_id == chat1.chat_id


# =============================================================================
# 5. Engine v2 _GenerationContext Customization
# =============================================================================


class TestGenerationContextCustomization:
    """Tests for _GenerationContext customization dict in engine_v2.py."""

    def _make_spec(self):
        """Return a minimal SystemSpec for testing."""
        from src.code_generation.architect import SystemSpec, TechStackSpec, RouteSpec, PageSpec, RoleSpec
        return SystemSpec(
            app_name="TestApp",
            description="A simple test application",
            entities=[],
            api_routes=[RouteSpec(path="/api/health", method="GET", description="Health check")],
            pages=[PageSpec(route="/", title="Home")],
            roles=[RoleSpec(name="user", permissions=["read"])],
            integrations=[],
            business_rules=["Users must be logged in"],
            tech_stack=TechStackSpec(),
        )

    def test_generation_context_accepts_customization_dict(self):
        """_GenerationContext can be instantiated with a customization dict."""
        from src.code_generation.engine_v2 import _GenerationContext

        spec = self._make_spec()
        custom = {
            "backend_framework": "django",
            "database": "sqlite",
            "auth_strategy": "session",
        }
        ctx = _GenerationContext(
            spec=spec,
            output_dir=Path("/tmp/output"),
            theme="Dark",
            customization=custom,
        )
        assert ctx.customization == custom
        assert ctx.customization["backend_framework"] == "django"

    def test_generation_context_default_empty_customization(self):
        """_GenerationContext customization defaults to an empty dict."""
        from src.code_generation.engine_v2 import _GenerationContext

        spec = self._make_spec()
        ctx = _GenerationContext(
            spec=spec,
            output_dir=Path("/tmp/output"),
            theme="Modern",
        )
        assert ctx.customization == {}

    def test_spec_summary_includes_customization_when_ctx_provided(self):
        """_spec_summary includes customization info when ctx is passed."""
        from src.code_generation.engine_v2 import _GenerationContext, _spec_summary

        spec = self._make_spec()
        ctx = _GenerationContext(
            spec=spec,
            output_dir=Path("/tmp/output"),
            theme="Modern",
            customization={
                "backend_framework": "django",
                "database": "mysql",
                "auth_strategy": "oauth2",
                "frontend_framework": "vue",
                "css_framework": "chakra",
                "deployment_target": "aws",
            },
        )
        summary = _spec_summary(spec, ctx=ctx)

        assert "Customization:" in summary
        assert "django" in summary
        assert "mysql" in summary
        assert "oauth2" in summary

    def test_spec_summary_without_ctx_has_no_customization(self):
        """_spec_summary without ctx does not include customization section."""
        from src.code_generation.engine_v2 import _spec_summary

        spec = self._make_spec()
        summary = _spec_summary(spec)

        assert "Customization:" not in summary

    def test_spec_summary_includes_extra_instructions(self):
        """_spec_summary includes extra_instructions when they are non-empty."""
        from src.code_generation.engine_v2 import _GenerationContext, _spec_summary

        spec = self._make_spec()
        ctx = _GenerationContext(
            spec=spec,
            output_dir=Path("/tmp/output"),
            theme="Modern",
            customization={
                "backend_framework": "fastapi",
                "database": "postgresql",
                "auth_strategy": "jwt",
                "frontend_framework": "nextjs",
                "css_framework": "tailwind",
                "deployment_target": "docker",
                "extra_instructions": "Use Stripe for payments",
            },
        )
        summary = _spec_summary(spec, ctx=ctx)

        assert "Use Stripe for payments" in summary

    def test_spec_summary_empty_ctx_customization_no_section(self):
        """_spec_summary with ctx but empty customization does not add section."""
        from src.code_generation.engine_v2 import _GenerationContext, _spec_summary

        spec = self._make_spec()
        ctx = _GenerationContext(
            spec=spec,
            output_dir=Path("/tmp/output"),
            theme="Modern",
            customization={},  # empty
        )
        summary = _spec_summary(spec, ctx=ctx)

        assert "Customization:" not in summary

    def test_spec_summary_compact_mode_omits_routes(self):
        """_spec_summary in compact mode omits API routes and business rules."""
        from src.code_generation.engine_v2 import _spec_summary

        spec = self._make_spec()
        summary_full = _spec_summary(spec, compact=False)
        summary_compact = _spec_summary(spec, compact=True)

        # Full should have API Routes section
        assert "API Routes:" in summary_full
        # Compact should not
        assert "API Routes:" not in summary_compact


# =============================================================================
# 6. ConsistencyResult Model
# =============================================================================


class TestConsistencyResult:
    """Tests for ConsistencyResult model correctness."""

    def test_consistency_result_initial_state(self):
        """ConsistencyResult initializes with empty fixes and warnings."""
        from src.code_generation.consistency import ConsistencyResult

        result = ConsistencyResult()
        assert result.fixes == []
        assert result.warnings == []
        assert result.total_fixes == 0

    def test_total_fixes_updates_dynamically(self):
        """total_fixes reflects the current length of the fixes list."""
        from src.code_generation.consistency import ConsistencyFix, ConsistencyResult

        result = ConsistencyResult()
        assert result.total_fixes == 0

        result.fixes.append(ConsistencyFix("a.py", "Fixed something", "import_fix"))
        assert result.total_fixes == 1

        result.fixes.append(ConsistencyFix("b.py", "Created init", "init_created"))
        assert result.total_fixes == 2

    def test_consistency_fix_attributes(self):
        """ConsistencyFix stores all three attributes correctly."""
        from src.code_generation.consistency import ConsistencyFix

        fix = ConsistencyFix(
            file_path="backend/app/routes/users.py",
            description="Fixed import: 'app.models.user' → 'backend.app.models.user'",
            fix_type="import_fix",
        )
        assert fix.file_path == "backend/app/routes/users.py"
        assert "import_fix" in fix.fix_type
        assert "app.models.user" in fix.description
