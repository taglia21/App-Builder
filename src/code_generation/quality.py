"""
Code Quality Pipeline — validates generated code for correctness, completeness,
and production-readiness.

Runs after code generation and before delivering output to the user.
"""

from __future__ import annotations

import ast
import asyncio
import logging
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field, model_validator

from src.llm.client import get_llm_client

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Standard-library module names (used for import classification)
# ---------------------------------------------------------------------------
_STDLIB_MODULES: frozenset[str] = frozenset(sys.stdlib_module_names)  # type: ignore[attr-defined]

# Common third-party packages that may appear in generated code
_KNOWN_THIRD_PARTY: frozenset[str] = frozenset(
    [
        "fastapi", "uvicorn", "pydantic", "sqlalchemy", "alembic",
        "aiohttp", "httpx", "requests", "starlette",
        "pytest", "anyio", "celery", "redis", "boto3", "botocore",
        "jose", "passlib", "bcrypt", "cryptography",
        "jinja2", "aiofiles", "psycopg2", "asyncpg", "pymongo",
        "motor", "stripe", "twilio", "sendgrid",
        "openai", "anthropic", "groq", "perplexity",
        "dotenv", "python_dotenv", "click", "typer",
        "loguru", "structlog", "prometheus_client",
        "sentry_sdk", "watchfiles", "email_validator",
        "yaml", "toml", "orjson", "ujson",
        "PIL", "Pillow", "numpy", "pandas",
        "src",  # local project root
    ]
)

# Patterns that signal a hardcoded secret
_SECRET_PATTERNS: list[tuple[str, str]] = [
    (r'(?i)(password|passwd|pwd)\s*=\s*["\'][^"\']{4,}["\']', "Hardcoded password"),
    (r'(?i)secret_key\s*=\s*["\'][^"\']{4,}["\']', "Hardcoded secret key"),
    (r'(?i)(api_key|apikey)\s*=\s*["\'][A-Za-z0-9_\-]{8,}["\']', "Hardcoded API key"),
    (r'(?i)token\s*=\s*["\'][A-Za-z0-9_\-\.]{20,}["\']', "Hardcoded token"),
    (r'(?i)(aws_secret|aws_access_key_id)\s*=\s*["\'][^"\']{8,}["\']', "Hardcoded AWS credential"),
]

# Patterns that signal SQL injection risk
_SQL_INJECTION_PATTERNS: list[tuple[str, str]] = [
    (r'execute\s*\(\s*f["\'].*SELECT', "f-string SQL query — SQL injection risk"),
    (r'execute\s*\(\s*f["\'].*INSERT', "f-string SQL INSERT — SQL injection risk"),
    (r'execute\s*\(\s*f["\'].*UPDATE', "f-string SQL UPDATE — SQL injection risk"),
    (r'execute\s*\(\s*f["\'].*DELETE', "f-string SQL DELETE — SQL injection risk"),
    (r'execute\s*\(\s*["\'].*%\s*\(', "%-format SQL query — SQL injection risk"),
    (r'\.format\s*\(.*\)\s*.*SELECT', ".format() SQL query — SQL injection risk"),
]

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class QualityCheck(BaseModel):
    """Result of a single quality check."""

    name: str
    category: str  # "syntax" | "imports" | "security" | "completeness" | "consistency"
    passed: bool
    severity: str  # "error" | "warning" | "info"
    message: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    fix_suggestion: Optional[str] = None


class QualityReport(BaseModel):
    """Aggregated result of the full quality pipeline."""

    passed: bool = False
    checks: List[QualityCheck] = Field(default_factory=list)
    errors: int = 0
    warnings: int = 0
    score: int = 0
    summary: str = ""

    @model_validator(mode="after")
    def _compute_derived(self) -> "QualityReport":
        self.errors = sum(1 for c in self.checks if c.severity == "error")
        self.warnings = sum(1 for c in self.checks if c.severity == "warning")
        self.passed = self.errors == 0
        self.score = _compute_score(self.checks)
        self.summary = _build_summary(self)
        return self


# ---------------------------------------------------------------------------
# Score helper
# ---------------------------------------------------------------------------


def _compute_score(checks: List[QualityCheck]) -> int:
    """Compute a 0-100 quality score from check results."""
    if not checks:
        return 100
    total = len(checks)
    errors = sum(1 for c in checks if not c.passed and c.severity == "error")
    warnings = sum(1 for c in checks if not c.passed and c.severity == "warning")
    # Deduct 10 pts per error, 3 pts per warning
    deduction = (errors * 10) + (warnings * 3)
    raw = max(0, 100 - deduction)
    return int(raw)


def _build_summary(report: QualityReport) -> str:
    """Human-readable one-liner summary."""
    if report.passed:
        return (
            f"All checks passed. Score: {report.score}/100. "
            f"{report.warnings} warning(s)."
        )
    return (
        f"Quality gate FAILED — {report.errors} error(s), "
        f"{report.warnings} warning(s). Score: {report.score}/100."
    )


# ---------------------------------------------------------------------------
# CodeQualityPipeline
# ---------------------------------------------------------------------------


class CodeQualityPipeline:
    """
    Runs a battery of static-analysis checks over a generated project directory.

    Call ``await pipeline.validate(output_dir, spec)`` to get a QualityReport.
    Checks run in parallel where they are independent.
    """

    def __init__(self) -> None:
        self._client = get_llm_client("auto")

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    async def validate(
        self, output_dir: str, spec: Optional[Dict[str, Any]] = None
    ) -> QualityReport:
        """
        Run all quality checks against *output_dir* and return a report.

        Parameters
        ----------
        output_dir:
            Path to the root of the generated project.
        spec:
            Optional app spec dict used for completeness checks.
        """
        root = Path(output_dir)
        if not root.exists():
            check = QualityCheck(
                name="directory_exists",
                category="completeness",
                passed=False,
                severity="error",
                message=f"Output directory does not exist: {output_dir}",
                fix_suggestion="Ensure code generation completed successfully before running quality checks.",
            )
            return QualityReport(checks=[check])

        logger.info("Starting quality pipeline on %s", output_dir)

        # Run independent checks in parallel
        results = await asyncio.gather(
            self._check_python_syntax(root),
            self._check_typescript_syntax(root),
            self._check_imports(root),
            self._check_security(root),
            self._check_docker(root),
            self._check_file_structure(root),
            return_exceptions=True,
        )

        checks: List[QualityCheck] = []
        for result in results:
            if isinstance(result, Exception):
                logger.warning("A quality check raised an exception: %s", result)
                checks.append(
                    QualityCheck(
                        name="check_exception",
                        category="completeness",
                        passed=False,
                        severity="warning",
                        message=f"A check raised an unexpected error: {result}",
                    )
                )
            else:
                checks.extend(result)  # type: ignore[arg-type]

        # Completeness and consistency depend on the results of other checks
        completeness_checks = await self._check_completeness(root, spec)
        consistency_checks = await self._check_consistency(root)
        checks.extend(completeness_checks)
        checks.extend(consistency_checks)

        report = QualityReport(checks=checks)
        logger.info("Quality pipeline complete: %s", report.summary)
        return report

    # ------------------------------------------------------------------
    # Individual check methods
    # ------------------------------------------------------------------

    async def _check_python_syntax(self, root: Path) -> List[QualityCheck]:
        """AST-parse every .py file and report syntax errors."""

        def _run() -> List[QualityCheck]:
            checks: List[QualityCheck] = []
            py_files = list(root.rglob("*.py"))
            if not py_files:
                checks.append(
                    QualityCheck(
                        name="python_files_exist",
                        category="syntax",
                        passed=False,
                        severity="warning",
                        message="No Python files found in output directory.",
                    )
                )
                return checks

            for py_file in py_files:
                rel = py_file.relative_to(root)
                try:
                    source = py_file.read_text(encoding="utf-8", errors="replace")
                    ast.parse(source, filename=str(rel))
                    checks.append(
                        QualityCheck(
                            name=f"python_syntax:{rel}",
                            category="syntax",
                            passed=True,
                            severity="info",
                            message=f"Syntax OK: {rel}",
                            file_path=str(rel),
                        )
                    )
                except SyntaxError as exc:
                    checks.append(
                        QualityCheck(
                            name=f"python_syntax:{rel}",
                            category="syntax",
                            passed=False,
                            severity="error",
                            message=f"Syntax error in {rel}: {exc.msg}",
                            file_path=str(rel),
                            line_number=exc.lineno,
                            fix_suggestion="Review and correct the syntax error at the indicated line.",
                        )
                    )
                except Exception as exc:  # noqa: BLE001
                    checks.append(
                        QualityCheck(
                            name=f"python_syntax:{rel}",
                            category="syntax",
                            passed=False,
                            severity="warning",
                            message=f"Could not parse {rel}: {exc}",
                            file_path=str(rel),
                        )
                    )
            return checks

        return await asyncio.to_thread(_run)

    async def _check_typescript_syntax(self, root: Path) -> List[QualityCheck]:
        """
        Basic TypeScript/JavaScript checks:
        - Balanced braces and brackets
        - No obvious dangling imports
        - Proper import statement structure
        """

        def _run() -> List[QualityCheck]:
            checks: List[QualityCheck] = []
            ts_files = list(root.rglob("*.ts")) + list(root.rglob("*.tsx"))
            if not ts_files:
                return checks  # Not every project has TypeScript

            for ts_file in ts_files:
                rel = ts_file.relative_to(root)
                try:
                    source = ts_file.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue

                # Check brace/bracket balance
                open_braces = source.count("{") - source.count("}")
                open_brackets = source.count("[") - source.count("]")
                open_parens = source.count("(") - source.count(")")

                if open_braces != 0:
                    checks.append(
                        QualityCheck(
                            name=f"ts_braces:{rel}",
                            category="syntax",
                            passed=False,
                            severity="error",
                            message=(
                                f"Unbalanced curly braces in {rel} "
                                f"(net: {open_braces:+d})"
                            ),
                            file_path=str(rel),
                            fix_suggestion="Ensure every opening '{' has a matching closing '}'.",
                        )
                    )
                elif open_brackets != 0:
                    checks.append(
                        QualityCheck(
                            name=f"ts_brackets:{rel}",
                            category="syntax",
                            passed=False,
                            severity="warning",
                            message=(
                                f"Unbalanced square brackets in {rel} "
                                f"(net: {open_brackets:+d})"
                            ),
                            file_path=str(rel),
                        )
                    )
                elif open_parens != 0:
                    checks.append(
                        QualityCheck(
                            name=f"ts_parens:{rel}",
                            category="syntax",
                            passed=False,
                            severity="warning",
                            message=(
                                f"Unbalanced parentheses in {rel} "
                                f"(net: {open_parens:+d})"
                            ),
                            file_path=str(rel),
                        )
                    )
                else:
                    checks.append(
                        QualityCheck(
                            name=f"ts_syntax:{rel}",
                            category="syntax",
                            passed=True,
                            severity="info",
                            message=f"Basic syntax OK: {rel}",
                            file_path=str(rel),
                        )
                    )

                # Check import statements are well-formed
                bad_imports = re.findall(
                    r'^import\s+(?!.*from\s+["\'])(?!.*\*\s+as\s+)(?!type\s+)(\w+)',
                    source,
                    re.MULTILINE,
                )
                for imp in bad_imports:
                    checks.append(
                        QualityCheck(
                            name=f"ts_import:{rel}:{imp}",
                            category="imports",
                            passed=False,
                            severity="warning",
                            message=f"Possibly malformed import '{imp}' in {rel}",
                            file_path=str(rel),
                            fix_suggestion=f"Verify: import {{ {imp} }} from '...' or import {imp} from '...'",
                        )
                    )

            return checks

        return await asyncio.to_thread(_run)

    async def _check_imports(self, root: Path) -> List[QualityCheck]:
        """
        For Python files:
        - Extract all import statements via AST
        - Flag imports of local modules that don't exist in the project
        - Allow stdlib and known third-party packages without flagging
        """

        def _run() -> List[QualityCheck]:
            checks: List[QualityCheck] = []
            py_files = list(root.rglob("*.py"))

            # Build set of available local modules (package directories + .py files)
            local_modules: set[str] = set()
            for f in py_files:
                # Module name relative to root, e.g. backend/app/main -> backend
                parts = f.relative_to(root).parts
                local_modules.add(parts[0])
                if len(parts) > 1:
                    local_modules.add(parts[1])

            for py_file in py_files:
                rel = py_file.relative_to(root)
                try:
                    source = py_file.read_text(encoding="utf-8", errors="replace")
                    tree = ast.parse(source, filename=str(rel))
                except (SyntaxError, OSError):
                    # Already reported in syntax check
                    continue

                for node in ast.walk(tree):
                    if isinstance(node, (ast.Import, ast.ImportFrom)):
                        if isinstance(node, ast.Import):
                            names = [alias.name.split(".")[0] for alias in node.names]
                        else:
                            # ImportFrom: module may be None for relative imports
                            if node.module is None:
                                continue  # relative import like `from . import x`
                            names = [node.module.split(".")[0]]

                        for top_name in names:
                            if not top_name:
                                continue
                            if top_name in _STDLIB_MODULES:
                                continue
                            if top_name in _KNOWN_THIRD_PARTY:
                                continue
                            # Check if it's a local module
                            candidate = root / top_name
                            if (
                                candidate.is_dir()
                                or (root / f"{top_name}.py").exists()
                                or top_name in local_modules
                            ):
                                continue
                            # Unknown import — flag as warning
                            checks.append(
                                QualityCheck(
                                    name=f"import_missing:{rel}:{top_name}",
                                    category="imports",
                                    passed=False,
                                    severity="warning",
                                    message=(
                                        f"Unknown import '{top_name}' in {rel} — "
                                        "not found in stdlib, known packages, or project."
                                    ),
                                    file_path=str(rel),
                                    line_number=node.lineno,
                                    fix_suggestion=(
                                        f"Add '{top_name}' to requirements.txt "
                                        "or verify the module path is correct."
                                    ),
                                )
                            )

            if not checks:
                checks.append(
                    QualityCheck(
                        name="imports_ok",
                        category="imports",
                        passed=True,
                        severity="info",
                        message="All Python imports resolved successfully.",
                    )
                )
            return checks

        return await asyncio.to_thread(_run)

    async def _check_security(self, root: Path) -> List[QualityCheck]:
        """
        Security checks:
        - Hardcoded secrets/passwords outside .env.example
        - SQL injection patterns
        - eval/exec usage
        - Missing CORS configuration
        - Weak/missing JWT settings
        """

        def _run() -> List[QualityCheck]:
            checks: List[QualityCheck] = []
            py_files = list(root.rglob("*.py"))

            cors_found = False
            jwt_secret_from_env = False
            jwt_algorithm_found = False

            for py_file in py_files:
                rel = py_file.relative_to(root)
                is_env_example = py_file.name in (".env.example", ".env.sample")

                try:
                    source = py_file.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue

                lines = source.splitlines()

                # --- Hardcoded secrets ---
                if not is_env_example:
                    for pattern, label in _SECRET_PATTERNS:
                        for lineno, line in enumerate(lines, start=1):
                            if re.search(pattern, line):
                                # Skip lines that read from env
                                if "os.getenv" in line or "os.environ" in line or "getenv" in line:
                                    continue
                                checks.append(
                                    QualityCheck(
                                        name=f"security_secret:{rel}:{lineno}",
                                        category="security",
                                        passed=False,
                                        severity="error",
                                        message=f"{label} detected in {rel}:{lineno}",
                                        file_path=str(rel),
                                        line_number=lineno,
                                        fix_suggestion=(
                                            "Move this value to an environment variable "
                                            "and read it with os.getenv()."
                                        ),
                                    )
                                )

                # --- SQL injection ---
                for pattern, label in _SQL_INJECTION_PATTERNS:
                    for lineno, line in enumerate(lines, start=1):
                        if re.search(pattern, line):
                            checks.append(
                                QualityCheck(
                                    name=f"security_sqli:{rel}:{lineno}",
                                    category="security",
                                    passed=False,
                                    severity="error",
                                    message=f"{label} in {rel}:{lineno}",
                                    file_path=str(rel),
                                    line_number=lineno,
                                    fix_suggestion=(
                                        "Use parameterised queries or ORM methods "
                                        "instead of string-formatting SQL."
                                    ),
                                )
                            )

                # --- eval / exec ---
                for lineno, line in enumerate(lines, start=1):
                    stripped = line.strip()
                    if re.search(r'\beval\s*\(', stripped) and not stripped.startswith("#"):
                        checks.append(
                            QualityCheck(
                                name=f"security_eval:{rel}:{lineno}",
                                category="security",
                                passed=False,
                                severity="error",
                                message=f"eval() usage in {rel}:{lineno} — arbitrary code execution risk",
                                file_path=str(rel),
                                line_number=lineno,
                                fix_suggestion="Avoid eval(); use ast.literal_eval() for safe evaluation.",
                            )
                        )
                    if re.search(r'\bexec\s*\(', stripped) and not stripped.startswith("#"):
                        checks.append(
                            QualityCheck(
                                name=f"security_exec:{rel}:{lineno}",
                                category="security",
                                passed=False,
                                severity="warning",
                                message=f"exec() usage in {rel}:{lineno} — potential code injection",
                                file_path=str(rel),
                                line_number=lineno,
                                fix_suggestion="Consider replacing exec() with explicit logic.",
                            )
                        )

                # --- CORS ---
                if "CORSMiddleware" in source or "add_middleware" in source:
                    cors_found = True

                # --- JWT ---
                if re.search(r'SECRET_KEY\s*=\s*os\.getenv', source):
                    jwt_secret_from_env = True
                if re.search(r'ALGORITHM\s*=\s*["\']HS(256|384|512)["\']', source):
                    jwt_algorithm_found = True

            # --- CORS global check ---
            if not cors_found:
                checks.append(
                    QualityCheck(
                        name="security_cors_missing",
                        category="security",
                        passed=False,
                        severity="warning",
                        message="No CORS middleware configuration detected in any Python file.",
                        fix_suggestion=(
                            "Add CORSMiddleware to your FastAPI/Starlette app "
                            "to control cross-origin requests."
                        ),
                    )
                )
            else:
                checks.append(
                    QualityCheck(
                        name="security_cors_present",
                        category="security",
                        passed=True,
                        severity="info",
                        message="CORS middleware configuration found.",
                    )
                )

            # --- JWT global check ---
            if not jwt_secret_from_env and any(
                (root / d).exists()
                for d in ["backend", "app", "src"]
            ):
                checks.append(
                    QualityCheck(
                        name="security_jwt_secret",
                        category="security",
                        passed=False,
                        severity="warning",
                        message="JWT SECRET_KEY does not appear to be loaded from environment variables.",
                        fix_suggestion="Ensure SECRET_KEY = os.getenv('SECRET_KEY') in your config.",
                    )
                )

            if jwt_algorithm_found:
                checks.append(
                    QualityCheck(
                        name="security_jwt_algorithm",
                        category="security",
                        passed=True,
                        severity="info",
                        message="JWT algorithm (HS256/384/512) properly configured.",
                    )
                )

            return checks

        return await asyncio.to_thread(_run)

    async def _check_completeness(
        self, root: Path, spec: Optional[Dict[str, Any]]
    ) -> List[QualityCheck]:
        """
        If a spec is provided, verify:
        - Every entity has a model file
        - Every entity has CRUD endpoints
        - Every entity has a schema
        - Every page listed in the spec exists
        - Auth endpoints exist
        """

        def _run() -> List[QualityCheck]:
            checks: List[QualityCheck] = []

            if not spec:
                checks.append(
                    QualityCheck(
                        name="completeness_no_spec",
                        category="completeness",
                        passed=True,
                        severity="info",
                        message="No spec provided — skipping spec-based completeness checks.",
                    )
                )
                return checks

            entities: List[str] = [
                e.get("name", "") if isinstance(e, dict) else str(e)
                for e in spec.get("entities", [])
            ]

            backend_root = _find_dir(root, ["backend/app", "app", "backend", "src"])
            frontend_root = _find_dir(root, ["frontend/src", "frontend", "client/src"])

            # --- Entity model files ---
            for entity in entities:
                entity_lower = entity.lower()
                model_candidates = [
                    backend_root / "models" / f"{entity_lower}.py",
                    backend_root / "models.py",
                    backend_root / f"models/{entity_lower}.py",
                ]
                if not any(c.exists() for c in model_candidates):
                    checks.append(
                        QualityCheck(
                            name=f"completeness_model:{entity}",
                            category="completeness",
                            passed=False,
                            severity="error",
                            message=f"Model file missing for entity '{entity}'",
                            fix_suggestion=f"Create {backend_root}/models/{entity_lower}.py",
                        )
                    )
                else:
                    checks.append(
                        QualityCheck(
                            name=f"completeness_model:{entity}",
                            category="completeness",
                            passed=True,
                            severity="info",
                            message=f"Model file present for entity '{entity}'",
                        )
                    )

                # --- CRUD endpoints ---
                crud_candidates = [
                    backend_root / "api" / f"{entity_lower}.py",
                    backend_root / "routers" / f"{entity_lower}.py",
                    backend_root / "routes" / f"{entity_lower}.py",
                    backend_root / "api" / "v1" / f"{entity_lower}.py",
                    backend_root / "crud" / f"{entity_lower}.py",
                ]
                if not any(c.exists() for c in crud_candidates):
                    checks.append(
                        QualityCheck(
                            name=f"completeness_crud:{entity}",
                            category="completeness",
                            passed=False,
                            severity="warning",
                            message=f"CRUD endpoint file missing for entity '{entity}'",
                            fix_suggestion=(
                                f"Create a router file for '{entity}' under "
                                f"{backend_root}/api/ or {backend_root}/routers/"
                            ),
                        )
                    )
                else:
                    checks.append(
                        QualityCheck(
                            name=f"completeness_crud:{entity}",
                            category="completeness",
                            passed=True,
                            severity="info",
                            message=f"CRUD endpoints present for entity '{entity}'",
                        )
                    )

                # --- Schemas ---
                schema_candidates = [
                    backend_root / "schemas" / f"{entity_lower}.py",
                    backend_root / "schemas.py",
                ]
                if not any(c.exists() for c in schema_candidates):
                    checks.append(
                        QualityCheck(
                            name=f"completeness_schema:{entity}",
                            category="completeness",
                            passed=False,
                            severity="warning",
                            message=f"Schema file missing for entity '{entity}'",
                            fix_suggestion=f"Create {backend_root}/schemas/{entity_lower}.py",
                        )
                    )
                else:
                    checks.append(
                        QualityCheck(
                            name=f"completeness_schema:{entity}",
                            category="completeness",
                            passed=True,
                            severity="info",
                            message=f"Schema present for entity '{entity}'",
                        )
                    )

            # --- Frontend pages ---
            if frontend_root:
                raw_pages = spec.get("pages", [])
                pages: List[str] = []
                for p in raw_pages:
                    if isinstance(p, dict):
                        pages.append(p.get("title", p.get("route", str(p))))
                    else:
                        pages.append(str(p))
                for page in pages:
                    page_lower = page.lower().replace(" ", "")
                    page_candidates = list(frontend_root.rglob(f"*{page_lower}*"))
                    if not page_candidates:
                        checks.append(
                            QualityCheck(
                                name=f"completeness_page:{page}",
                                category="completeness",
                                passed=False,
                                severity="warning",
                                message=f"Frontend page '{page}' not found under {frontend_root}",
                                fix_suggestion=f"Create a page component for '{page}'.",
                            )
                        )
                    else:
                        checks.append(
                            QualityCheck(
                                name=f"completeness_page:{page}",
                                category="completeness",
                                passed=True,
                                severity="info",
                                message=f"Frontend page '{page}' present.",
                            )
                        )

            # --- Auth endpoints ---
            if spec.get("auth", True):
                auth_candidates = [
                    backend_root / "api" / "auth.py",
                    backend_root / "routers" / "auth.py",
                    backend_root / "routes" / "auth.py",
                    backend_root / "auth.py",
                ]
                if not any(c.exists() for c in auth_candidates):
                    checks.append(
                        QualityCheck(
                            name="completeness_auth",
                            category="completeness",
                            passed=False,
                            severity="error",
                            message="Auth endpoint file not found.",
                            fix_suggestion="Create backend/app/api/auth.py with login, register, and token endpoints.",
                        )
                    )
                else:
                    checks.append(
                        QualityCheck(
                            name="completeness_auth",
                            category="completeness",
                            passed=True,
                            severity="info",
                            message="Auth endpoints present.",
                        )
                    )

            return checks

        return await asyncio.to_thread(_run)

    async def _check_consistency(self, root: Path) -> List[QualityCheck]:
        """
        Cross-file consistency checks:
        - Model field names vs schema field names
        - API route names vs model names
        - TypeScript interface names vs backend schemas
        - Import path consistency
        """

        def _run() -> List[QualityCheck]:
            checks: List[QualityCheck] = []
            backend_root = _find_dir(root, ["backend/app", "app", "backend"])

            # --- Model vs schema field alignment ---
            models_dir = backend_root / "models" if backend_root else None
            schemas_dir = backend_root / "schemas" if backend_root else None

            if models_dir and models_dir.is_dir() and schemas_dir and schemas_dir.is_dir():
                for model_file in models_dir.glob("*.py"):
                    entity = model_file.stem
                    schema_file = schemas_dir / f"{entity}.py"
                    if not schema_file.exists():
                        continue

                    model_fields = _extract_class_fields(model_file)
                    schema_fields = _extract_class_fields(schema_file)

                    missing_in_schema = model_fields - schema_fields - {"id", "created_at", "updated_at"}
                    if missing_in_schema:
                        checks.append(
                            QualityCheck(
                                name=f"consistency_schema_fields:{entity}",
                                category="consistency",
                                passed=False,
                                severity="warning",
                                message=(
                                    f"Entity '{entity}': model fields not reflected in schema: "
                                    f"{', '.join(sorted(missing_in_schema))}"
                                ),
                                file_path=str(schema_file.relative_to(root)),
                                fix_suggestion=f"Add missing fields to {schema_file.name}.",
                            )
                        )
                    else:
                        checks.append(
                            QualityCheck(
                                name=f"consistency_schema_fields:{entity}",
                                category="consistency",
                                passed=True,
                                severity="info",
                                message=f"Model and schema fields aligned for '{entity}'.",
                            )
                        )

            # --- API route names vs model names ---
            api_dir = _find_dir(root, ["backend/app/api", "app/api", "backend/api"])
            if api_dir and api_dir.is_dir() and models_dir and models_dir.is_dir():
                model_names = {f.stem for f in models_dir.glob("*.py") if f.stem != "__init__"}
                for route_file in api_dir.glob("*.py"):
                    if route_file.stem in ("__init__", "deps", "dependencies", "auth"):
                        continue
                    route_entity = route_file.stem
                    if route_entity not in model_names:
                        checks.append(
                            QualityCheck(
                                name=f"consistency_route_model:{route_entity}",
                                category="consistency",
                                passed=False,
                                severity="warning",
                                message=(
                                    f"Route file '{route_entity}.py' has no matching model "
                                    f"in {models_dir.relative_to(root)}"
                                ),
                                file_path=str(route_file.relative_to(root)),
                                fix_suggestion=f"Create models/{route_entity}.py or rename the route file.",
                            )
                        )

            # --- TypeScript types vs backend schemas ---
            frontend_types_dir = _find_dir(
                root, ["frontend/src/types", "frontend/src/lib/types", "client/src/types"]
            )
            if frontend_types_dir and frontend_types_dir.is_dir() and schemas_dir and schemas_dir.is_dir():
                backend_entities = {f.stem for f in schemas_dir.glob("*.py") if f.stem != "__init__"}
                ts_types = set()
                for ts_file in frontend_types_dir.rglob("*.ts"):
                    source = ts_file.read_text(encoding="utf-8", errors="replace")
                    found = re.findall(r'(?:interface|type)\s+(\w+)', source)
                    ts_types.update(name.lower() for name in found)

                for entity in backend_entities:
                    if entity not in ts_types:
                        checks.append(
                            QualityCheck(
                                name=f"consistency_ts_types:{entity}",
                                category="consistency",
                                passed=False,
                                severity="warning",
                                message=(
                                    f"Backend schema '{entity}' has no matching TypeScript type/interface."
                                ),
                                fix_suggestion=f"Add a TypeScript interface for '{entity}' in {frontend_types_dir.relative_to(root)}/",
                            )
                        )

            # --- Import path consistency (relative vs absolute) ---
            py_files = list(root.rglob("*.py"))
            mixed_import_files: list[str] = []
            for py_file in py_files:
                try:
                    source = py_file.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue
                has_relative = bool(re.search(r'from \.\w', source))
                has_absolute_src = bool(re.search(r'from src\.', source))
                if has_relative and has_absolute_src:
                    mixed_import_files.append(str(py_file.relative_to(root)))

            if mixed_import_files:
                for f in mixed_import_files:
                    checks.append(
                        QualityCheck(
                            name=f"consistency_import_style:{f}",
                            category="consistency",
                            passed=False,
                            severity="warning",
                            message=f"Mixed relative and absolute imports in {f}",
                            file_path=f,
                            fix_suggestion="Use either relative OR absolute imports consistently per file.",
                        )
                    )

            if not checks:
                checks.append(
                    QualityCheck(
                        name="consistency_ok",
                        category="consistency",
                        passed=True,
                        severity="info",
                        message="Cross-file consistency checks passed.",
                    )
                )
            return checks

        return await asyncio.to_thread(_run)

    async def _check_docker(self, root: Path) -> List[QualityCheck]:
        """
        Docker checks:
        - docker-compose.yml exists
        - Referenced service names have corresponding Dockerfiles
        - Services reference valid image names or build contexts
        """

        def _run() -> List[QualityCheck]:
            checks: List[QualityCheck] = []
            compose_file = root / "docker-compose.yml"
            compose_file_alt = root / "docker-compose.yaml"

            target = compose_file if compose_file.exists() else (
                compose_file_alt if compose_file_alt.exists() else None
            )

            if target is None:
                checks.append(
                    QualityCheck(
                        name="docker_compose_missing",
                        category="completeness",
                        passed=False,
                        severity="warning",
                        message="docker-compose.yml not found in project root.",
                        fix_suggestion="Add a docker-compose.yml to enable one-command local setup.",
                    )
                )
                return checks

            checks.append(
                QualityCheck(
                    name="docker_compose_exists",
                    category="completeness",
                    passed=True,
                    severity="info",
                    message=f"docker-compose file found: {target.name}",
                )
            )

            # Parse service names and their build contexts
            compose_source = target.read_text(encoding="utf-8", errors="replace")
            service_builds = re.findall(
                r'build:\s*\n\s+context:\s*(\S+)', compose_source
            )
            service_builds_inline = re.findall(r'build:\s*(\./\S+)', compose_source)
            all_contexts = service_builds + service_builds_inline

            for context in all_contexts:
                context_path = (root / context).resolve()
                dockerfile = context_path / "Dockerfile"
                if not dockerfile.exists():
                    checks.append(
                        QualityCheck(
                            name=f"docker_dockerfile:{context}",
                            category="completeness",
                            passed=False,
                            severity="error",
                            message=f"Dockerfile missing for build context '{context}'",
                            file_path=str(target.relative_to(root)),
                            fix_suggestion=f"Create a Dockerfile at {context_path}/Dockerfile",
                        )
                    )
                else:
                    checks.append(
                        QualityCheck(
                            name=f"docker_dockerfile:{context}",
                            category="completeness",
                            passed=True,
                            severity="info",
                            message=f"Dockerfile present for context '{context}'",
                        )
                    )

            # Warn on hardcoded passwords in compose
            for lineno, line in enumerate(compose_source.splitlines(), start=1):
                if re.search(r'(?i)(POSTGRES_PASSWORD|MYSQL_ROOT_PASSWORD|password)\s*:\s*\S+', line):
                    if "${" not in line:  # not using env substitution
                        checks.append(
                            QualityCheck(
                                name=f"docker_secret:{lineno}",
                                category="security",
                                passed=False,
                                severity="warning",
                                message=f"Hardcoded password in docker-compose.yml:{lineno}",
                                file_path=str(target.relative_to(root)),
                                line_number=lineno,
                                fix_suggestion="Use environment variable substitution: ${POSTGRES_PASSWORD}",
                            )
                        )

            return checks

        return await asyncio.to_thread(_run)

    async def _check_file_structure(self, root: Path) -> List[QualityCheck]:
        """Verify expected directory structure: backend/app/, frontend/src/, etc."""

        def _run() -> List[QualityCheck]:
            checks: List[QualityCheck] = []
            expected_structures = [
                # (description, list of candidate paths — any one counts)
                ("Backend app directory", ["backend/app", "app", "backend/src"]),
                ("Frontend source directory", ["frontend/src", "frontend", "client/src"]),
                ("Backend requirements file", ["backend/requirements.txt", "requirements.txt"]),
                ("Environment example file", [".env.example", ".env.sample", "backend/.env.example"]),
                ("README file", ["README.md", "README.rst", "README.txt"]),
            ]

            for label, candidates in expected_structures:
                found = any((root / c).exists() for c in candidates)
                checks.append(
                    QualityCheck(
                        name=f"structure:{label.lower().replace(' ', '_')}",
                        category="completeness",
                        passed=found,
                        severity="warning" if not found else "info",
                        message=f"{label} {'found' if found else 'NOT found'}",
                        fix_suggestion=(
                            None
                            if found
                            else f"Create one of: {', '.join(candidates)}"
                        ),
                    )
                )

            return checks

        return await asyncio.to_thread(_run)


# ---------------------------------------------------------------------------
# AutoFixer
# ---------------------------------------------------------------------------


class AutoFixer:
    """
    Attempts to automatically fix quality issues reported by CodeQualityPipeline.

    Strategies:
    - Syntax errors: send broken source + error message to LLM, write back the fix.
    - Missing imports: insert the missing import statement at the top of the file.
    - Missing files: ask LLM to generate the file from context.
    """

    def __init__(self) -> None:
        self._client = get_llm_client("auto")

    async def fix(
        self, output_dir: str, report: QualityReport
    ) -> Tuple[int, QualityReport]:
        """
        Attempt to fix all fixable issues in *report*.

        Returns
        -------
        (fixes_applied, new_report)
            ``fixes_applied`` is the number of successful fixes.
            ``new_report`` is the result of re-running the pipeline.
        """
        root = Path(output_dir)
        fixes_applied = 0

        # Group failed checks by category
        failed = [c for c in report.checks if not c.passed]

        # Run auto-fix attempts
        syntax_fixes = await self._fix_syntax_errors(root, failed)
        import_fixes = await self._fix_missing_imports(root, failed)
        file_fixes = await self._fix_missing_files(root, failed)

        fixes_applied = syntax_fixes + import_fixes + file_fixes

        if fixes_applied > 0:
            logger.info("AutoFixer applied %d fix(es); re-running pipeline.", fixes_applied)
            pipeline = CodeQualityPipeline()
            new_report = await pipeline.validate(output_dir)
        else:
            new_report = report

        return fixes_applied, new_report

    # ------------------------------------------------------------------
    # Private fix methods
    # ------------------------------------------------------------------

    async def _fix_syntax_errors(
        self, root: Path, failed: List[QualityCheck]
    ) -> int:
        """Send each broken Python file to the LLM and write back the corrected version."""
        syntax_errors = [
            c for c in failed
            if c.category == "syntax"
            and c.file_path
            and c.file_path.endswith(".py")
        ]

        fixed = 0
        for check in syntax_errors:
            file_path = root / check.file_path
            if not file_path.exists():
                continue
            try:
                source = file_path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue

            prompt = (
                f"The following Python file has a syntax error:\n\n"
                f"Error: {check.message}\n"
                f"Line: {check.line_number}\n\n"
                f"```python\n{source}\n```\n\n"
                "Return ONLY the corrected Python source code. "
                "Do not include any explanation or markdown fences."
            )

            try:
                response = await asyncio.to_thread(
                    self._client.complete,
                    prompt,
                    None,
                    4096,
                    0.2,
                    False,
                )
                corrected = _strip_code_fences(response.content)
                # Validate the fix before writing
                ast.parse(corrected)
                file_path.write_text(corrected, encoding="utf-8")
                logger.info("AutoFixer: fixed syntax error in %s", check.file_path)
                fixed += 1
            except SyntaxError:
                logger.warning("AutoFixer: LLM fix for %s still has syntax errors; skipping.", check.file_path)
            except Exception as exc:  # noqa: BLE001
                logger.warning("AutoFixer: failed to fix %s: %s", check.file_path, exc)

        return fixed

    async def _fix_missing_imports(
        self, root: Path, failed: List[QualityCheck]
    ) -> int:
        """Add missing import statements to Python files."""
        import_errors = [
            c for c in failed
            if c.category == "imports"
            and c.file_path
            and c.file_path.endswith(".py")
        ]

        fixed = 0
        # Group by file to batch inserts
        by_file: Dict[str, List[QualityCheck]] = {}
        for check in import_errors:
            by_file.setdefault(check.file_path, []).append(check)

        for rel_path, checks in by_file.items():
            file_path = root / rel_path
            if not file_path.exists():
                continue
            try:
                source = file_path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue

            # Extract module names from check names: "import_missing:{rel}:{module}"
            modules = set()
            for check in checks:
                parts = check.name.split(":")
                if len(parts) >= 3:
                    modules.add(parts[-1])

            if not modules:
                continue

            # Build import lines
            new_imports = "\n".join(f"import {m}" for m in sorted(modules))
            patched = new_imports + "\n" + source

            try:
                ast.parse(patched)
                file_path.write_text(patched, encoding="utf-8")
                logger.info("AutoFixer: added imports %s to %s", modules, rel_path)
                fixed += 1
            except SyntaxError:
                logger.warning("AutoFixer: patched imports created syntax error in %s; skipping.", rel_path)
            except OSError as exc:
                logger.warning("AutoFixer: could not write %s: %s", rel_path, exc)

        return fixed

    async def _fix_missing_files(
        self, root: Path, failed: List[QualityCheck]
    ) -> int:
        """Generate missing files (models, schemas, routes) using the LLM."""
        missing_file_checks = [
            c for c in failed
            if c.category == "completeness"
            and c.fix_suggestion
            and "Create" in c.fix_suggestion
            and not c.passed
        ]

        fixed = 0
        for check in missing_file_checks:
            # Try to extract a file path from the fix suggestion
            match = re.search(r'Create\s+([\w/\.\-\_]+\.py)', check.fix_suggestion or "")
            if not match:
                continue

            rel_target = match.group(1).lstrip("/")
            target_path = root / rel_target

            if target_path.exists():
                continue

            # Ask LLM to generate the file
            context_files = _gather_context_files(root, target_path, max_files=3)
            context_block = "\n\n".join(
                f"# {name}\n```python\n{content}\n```"
                for name, content in context_files
            )

            prompt = (
                f"Generate a production-quality Python file for a FastAPI application.\n\n"
                f"File to create: {rel_target}\n"
                f"Reason needed: {check.message}\n\n"
                f"Context from existing project files:\n{context_block}\n\n"
                "Return ONLY the Python source code. No markdown fences, no explanation."
            )

            try:
                response = await asyncio.to_thread(
                    self._client.complete,
                    prompt,
                    None,
                    4096,
                    0.3,
                    False,
                )
                content = _strip_code_fences(response.content)
                # Validate before writing
                if target_path.suffix == ".py":
                    ast.parse(content)
                target_path.parent.mkdir(parents=True, exist_ok=True)
                target_path.write_text(content, encoding="utf-8")
                logger.info("AutoFixer: generated missing file %s", rel_target)
                fixed += 1
            except SyntaxError as exc:
                logger.warning("AutoFixer: generated file %s has syntax errors: %s; skipping.", rel_target, exc)
            except Exception as exc:  # noqa: BLE001
                logger.warning("AutoFixer: could not generate %s: %s", rel_target, exc)

        return fixed


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------


def _find_dir(root: Path, candidates: List[str]) -> Path:
    """Return the first candidate directory that exists under root, or root itself."""
    for c in candidates:
        path = root / c
        if path.is_dir():
            return path
    return root


def _extract_class_fields(py_file: Path) -> set[str]:
    """
    Parse a Python file and return the set of field/attribute names defined
    inside class bodies (SQLAlchemy columns or Pydantic fields).
    """
    try:
        source = py_file.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source)
    except (SyntaxError, OSError):
        return set()

    fields: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for item in node.body:
                # class Foo(Base): name = Column(...)
                if isinstance(item, ast.Assign):
                    for target in item.targets:
                        if isinstance(target, ast.Name):
                            fields.add(target.id)
                # class Foo(BaseModel): name: str
                elif isinstance(item, ast.AnnAssign):
                    if isinstance(item.target, ast.Name):
                        fields.add(item.target.id)
    return fields


def _strip_code_fences(text: str) -> str:
    """Remove markdown code fences from LLM output."""
    text = text.strip()
    # Remove ```python ... ``` or ``` ... ```
    text = re.sub(r'^```(?:python)?\s*\n', '', text)
    text = re.sub(r'\n```\s*$', '', text)
    return text.strip()


def _gather_context_files(
    root: Path, target: Path, max_files: int = 3
) -> List[Tuple[str, str]]:
    """
    Gather a few existing Python files from the same package directory
    to use as context for LLM generation.
    """
    parent = target.parent
    results: List[Tuple[str, str]] = []

    for sibling in sorted(parent.glob("*.py")):
        if sibling.stem == "__init__":
            continue
        try:
            content = sibling.read_text(encoding="utf-8", errors="replace")[:2000]
            results.append((str(sibling.relative_to(root)), content))
        except OSError:
            continue
        if len(results) >= max_files:
            break

    return results
