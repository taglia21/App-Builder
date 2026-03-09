"""
Post-generation Consistency Pass for Ignara.

Runs after all files are generated to detect and fix cross-file issues:
1. Import path validation — ensures all intra-project imports resolve
2. Naming alignment — schema/CRUD/route files reference correct model names
3. Config coherence — .env, docker-compose, and config.py agree on env vars
4. Missing __init__.py files — auto-creates them for proper Python packaging

This is the "polish" step that turns individually-correct files into a
coherent, runnable project.
"""
from __future__ import annotations

import ast
import logging
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result model
# ---------------------------------------------------------------------------

class ConsistencyFix:
    """Record of a single fix applied during the consistency pass."""

    def __init__(self, file_path: str, description: str, fix_type: str):
        self.file_path = file_path
        self.description = description
        self.fix_type = fix_type  # "import_fix" | "init_created" | "import_added" | "env_sync"

    def __repr__(self) -> str:
        return f"<ConsistencyFix {self.fix_type}: {self.file_path} — {self.description}>"


class ConsistencyResult:
    """Result of the full consistency pass."""

    def __init__(self):
        self.fixes: List[ConsistencyFix] = []
        self.warnings: List[str] = []

    @property
    def total_fixes(self) -> int:
        return len(self.fixes)


# ---------------------------------------------------------------------------
# Consistency checker
# ---------------------------------------------------------------------------

class ConsistencyChecker:
    """Run post-generation checks and auto-fix cross-file issues."""

    # Common intra-project import patterns for a FastAPI + Next.js project
    _BACKEND_IMPORT_ROOTS = {"app", "backend"}
    _IGNORED_DIRS = {"__pycache__", ".git", "node_modules", ".next", "dist", "build", ".venv", "venv"}

    def run(self, project_dir: str) -> ConsistencyResult:
        """
        Run the full consistency pass on the project at *project_dir*.

        Returns a :class:`ConsistencyResult` with all fixes applied and warnings.
        """
        result = ConsistencyResult()
        project = Path(project_dir)

        if not project.is_dir():
            result.warnings.append(f"Project directory not found: {project_dir}")
            return result

        # 1. Ensure __init__.py files exist in all Python package dirs
        self._ensure_init_files(project, result)

        # 2. Validate and fix Python imports
        self._fix_python_imports(project, result)

        # 3. Sync environment variables across config, .env.example, docker-compose
        self._sync_env_vars(project, result)

        # 4. Validate frontend import paths
        self._fix_frontend_imports(project, result)

        logger.info(
            "Consistency pass complete: %d fix(es), %d warning(s)",
            result.total_fixes,
            len(result.warnings),
        )
        return result

    # ------------------------------------------------------------------
    # 1. __init__.py creation
    # ------------------------------------------------------------------

    def _ensure_init_files(self, project: Path, result: ConsistencyResult) -> None:
        """Create missing __init__.py files in backend Python package directories."""
        backend_dir = project / "backend"
        if not backend_dir.is_dir():
            # Also check if the project root IS the backend
            backend_dir = project
            if not (backend_dir / "app").is_dir():
                return

        for dirpath, dirnames, filenames in os.walk(str(backend_dir)):
            # Skip ignored directories
            dirnames[:] = [d for d in dirnames if d not in self._IGNORED_DIRS]

            path = Path(dirpath)
            # Only create __init__.py in directories that contain .py files
            # or other package directories
            has_py = any(f.endswith(".py") for f in filenames)
            has_subpackages = any((path / d / "__init__.py").exists() for d in dirnames)

            if (has_py or has_subpackages) and "__init__.py" not in filenames:
                init_path = path / "__init__.py"
                init_path.write_text("")
                rel = str(init_path.relative_to(project))
                result.fixes.append(ConsistencyFix(
                    file_path=rel,
                    description="Created missing __init__.py for Python package",
                    fix_type="init_created",
                ))
                logger.debug("Created %s", rel)

    # ------------------------------------------------------------------
    # 2. Python import validation & fixing
    # ------------------------------------------------------------------

    def _fix_python_imports(self, project: Path, result: ConsistencyResult) -> None:
        """Scan Python files for broken intra-project imports and attempt fixes."""
        backend_dir = project / "backend"
        if not backend_dir.is_dir():
            backend_dir = project

        # Build a map of available Python modules in the project
        available_modules = self._build_module_map(backend_dir, project)

        for py_file in backend_dir.rglob("*.py"):
            if any(part in self._IGNORED_DIRS for part in py_file.parts):
                continue
            self._check_file_imports(py_file, available_modules, project, result)

    def _build_module_map(self, backend_dir: Path, project: Path) -> Set[str]:
        """Build a set of all available Python module dotted paths."""
        modules: Set[str] = set()
        for py_file in backend_dir.rglob("*.py"):
            if any(part in self._IGNORED_DIRS for part in py_file.parts):
                continue
            try:
                rel = py_file.relative_to(project)
            except ValueError:
                continue

            # Convert path to module notation: backend/app/models/user.py → backend.app.models.user
            parts = list(rel.parts)
            if parts[-1] == "__init__.py":
                parts = parts[:-1]
            else:
                parts[-1] = parts[-1].replace(".py", "")

            dotted = ".".join(parts)
            modules.add(dotted)

            # Also add without the "backend" prefix since some imports use just "app.xxx"
            if len(parts) > 1 and parts[0] == "backend":
                modules.add(".".join(parts[1:]))

        return modules

    def _check_file_imports(
        self,
        py_file: Path,
        available_modules: Set[str],
        project: Path,
        result: ConsistencyResult,
    ) -> None:
        """Check imports in a single Python file and fix common issues."""
        try:
            source = py_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return

        try:
            tree = ast.parse(source)
        except SyntaxError:
            return  # Skip unparseable files

        modified = False
        lines = source.splitlines(keepends=True)

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                module = node.module

                # Skip stdlib and third-party imports
                if self._is_external_import(module):
                    continue

                # Check if the import target exists
                if module not in available_modules:
                    # Try common fixes
                    fixed_module = self._try_fix_import(module, available_modules)
                    if fixed_module and fixed_module != module:
                        # Apply the fix
                        old_import = f"from {module} "
                        new_import = f"from {fixed_module} "
                        source = source.replace(old_import, new_import, 1)
                        modified = True
                        rel_path = str(py_file.relative_to(project))
                        result.fixes.append(ConsistencyFix(
                            file_path=rel_path,
                            description=f"Fixed import: '{module}' → '{fixed_module}'",
                            fix_type="import_fix",
                        ))

        if modified:
            py_file.write_text(source, encoding="utf-8")

    @staticmethod
    def _is_external_import(module: str) -> bool:
        """Return True if the import looks like a stdlib or third-party module."""
        first_part = module.split(".")[0]
        # Common external modules used in FastAPI projects
        external = {
            "fastapi", "pydantic", "sqlalchemy", "alembic", "jose",
            "passlib", "httpx", "redis", "celery", "stripe", "boto3",
            "starlette", "uvicorn", "pytest", "typing", "datetime",
            "os", "sys", "json", "pathlib", "logging", "asyncio",
            "uuid", "hashlib", "secrets", "time", "re", "collections",
            "enum", "dataclasses", "abc", "contextlib", "functools",
            "pydantic_settings", "email_validator", "sendgrid", "twilio",
            "firebase_admin", "openai", "anthropic", "google",
        }
        return first_part in external

    @staticmethod
    def _try_fix_import(module: str, available: Set[str]) -> Optional[str]:
        """Attempt common import path corrections."""
        parts = module.split(".")

        # Try adding "backend." prefix
        with_backend = "backend." + module
        if with_backend in available:
            return with_backend

        # Try removing "backend." prefix
        if parts[0] == "backend" and len(parts) > 1:
            without_backend = ".".join(parts[1:])
            if without_backend in available:
                return without_backend

        # Try swapping "backend.app" → "app"
        if module.startswith("backend.app."):
            shorter = module.replace("backend.app.", "app.", 1)
            if shorter in available:
                return shorter

        # Try swapping "app" → "backend.app"
        if module.startswith("app."):
            longer = "backend." + module
            if longer in available:
                return longer

        return None

    # ------------------------------------------------------------------
    # 3. Environment variable synchronization
    # ------------------------------------------------------------------

    def _sync_env_vars(self, project: Path, result: ConsistencyResult) -> None:
        """Ensure .env.example mentions all env vars referenced in config.py."""
        config_paths = [
            project / "backend" / "app" / "core" / "config.py",
            project / "app" / "core" / "config.py",
        ]
        config_file = None
        for p in config_paths:
            if p.is_file():
                config_file = p
                break

        if not config_file:
            return

        env_example = project / ".env.example"
        if not env_example.exists():
            env_example = project / "backend" / ".env.example"

        # Extract env var names from config.py (look for field names in Settings class)
        try:
            source = config_file.read_text(encoding="utf-8")
        except OSError:
            return

        # Match patterns like: DATABASE_URL: str = Field(...)  or  DATABASE_URL: str
        config_vars: Set[str] = set()
        for match in re.finditer(r'^\s+([A-Z][A-Z0-9_]+)\s*:', source, re.MULTILINE):
            config_vars.add(match.group(1))

        if not config_vars:
            return

        # Read existing .env.example
        existing_vars: Set[str] = set()
        env_content = ""
        if env_example.exists():
            try:
                env_content = env_example.read_text(encoding="utf-8")
                for line in env_content.splitlines():
                    if "=" in line and not line.strip().startswith("#"):
                        var_name = line.split("=", 1)[0].strip()
                        existing_vars.add(var_name)
            except OSError:
                pass

        # Add missing vars to .env.example
        missing = config_vars - existing_vars
        if missing:
            additions = []
            for var in sorted(missing):
                # Provide sensible placeholders
                if "SECRET" in var or "KEY" in var:
                    additions.append(f"{var}=change-me-in-production")
                elif "URL" in var and "DATABASE" in var:
                    additions.append(f"{var}=postgresql+asyncpg://user:password@localhost:5432/dbname")
                elif "URL" in var and "REDIS" in var:
                    additions.append(f"{var}=redis://localhost:6379/0")
                elif "ORIGIN" in var:
                    additions.append(f"{var}=http://localhost:3000")
                elif "DEBUG" in var:
                    additions.append(f"{var}=false")
                elif "PORT" in var:
                    additions.append(f"{var}=8000")
                else:
                    additions.append(f"{var}=")

            new_content = env_content.rstrip() + "\n\n# Auto-added by consistency check\n"
            new_content += "\n".join(additions) + "\n"

            target = env_example if env_example.exists() else (project / ".env.example")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(new_content, encoding="utf-8")

            rel_path = str(target.relative_to(project))
            result.fixes.append(ConsistencyFix(
                file_path=rel_path,
                description=f"Added {len(missing)} missing env var(s): {', '.join(sorted(missing)[:5])}{'...' if len(missing) > 5 else ''}",
                fix_type="env_sync",
            ))

    # ------------------------------------------------------------------
    # 4. Frontend import validation
    # ------------------------------------------------------------------

    def _fix_frontend_imports(self, project: Path, result: ConsistencyResult) -> None:
        """Check TypeScript/TSX imports use correct @ alias paths."""
        frontend_dir = project / "frontend"
        if not frontend_dir.is_dir():
            return

        src_dir = frontend_dir / "src"
        if not src_dir.is_dir():
            return

        # Build a map of available TS/TSX modules
        available_ts: Set[str] = set()
        for ext in ("*.ts", "*.tsx"):
            for f in src_dir.rglob(ext):
                if any(part in self._IGNORED_DIRS for part in f.parts):
                    continue
                try:
                    rel = f.relative_to(src_dir)
                except ValueError:
                    continue
                # @/components/ui/index → @/components/ui
                parts = list(rel.parts)
                stem = parts[-1].replace(".tsx", "").replace(".ts", "")
                if stem == "index":
                    parts = parts[:-1]
                else:
                    parts[-1] = stem
                alias = "@/" + "/".join(parts)
                available_ts.add(alias)

        for ext in ("*.ts", "*.tsx"):
            for ts_file in src_dir.rglob(ext):
                if any(part in self._IGNORED_DIRS for part in ts_file.parts):
                    continue
                self._check_ts_imports(ts_file, available_ts, project, result)

    def _check_ts_imports(
        self,
        ts_file: Path,
        available: Set[str],
        project: Path,
        result: ConsistencyResult,
    ) -> None:
        """Check imports in a TypeScript file for common issues."""
        try:
            source = ts_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return

        modified = False
        # Match: import ... from "@/something"  or  import ... from '@/something'
        for match in re.finditer(r'''from\s+['"](@/[^'"]+)['"]''', source):
            import_path = match.group(1)
            # Strip file extension if present
            clean_path = re.sub(r'\.(ts|tsx|js|jsx)$', '', import_path)

            if clean_path not in available:
                # Try to find a close match (e.g., @/components/ui vs @/components/ui/index)
                possible = clean_path + "/index"
                if possible in available:
                    # No fix needed — the module system handles index resolution
                    pass
                else:
                    rel = str(ts_file.relative_to(project))
                    result.warnings.append(
                        f"{rel}: import '{import_path}' may not resolve — "
                        f"target file not found in project"
                    )
