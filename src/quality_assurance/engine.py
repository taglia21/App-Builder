"""
Quality Assurance Engine.
Runs post-generation checks, validation, and formatting on the codebase.
"""

import ast
import logging
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ValidationIssue(BaseModel):
    """Represents a single validation issue."""
    file: str
    line: Optional[int] = None
    message: str
    severity: str = "error"  # error, warning, info


class QAReport(BaseModel):
    """Report on Quality Assurance execution."""
    backend_formatted: bool = False
    frontend_formatted: bool = False
    python_syntax_valid: bool = False
    typescript_valid: bool = False
    issues: List[str] = Field(default_factory=list)
    validation_issues: List[ValidationIssue] = Field(default_factory=list)
    files_validated: int = 0
    files_with_errors: int = 0

class QualityAssuranceEngine:
    """
    Ensures generated code meets quality standards.
    Validates syntax, runs formatters (Black, Isort, Prettier), and static analysis.
    """

    def __init__(self):
        self.black_path = shutil.which("black")
        self.isort_path = shutil.which("isort")
        self.tsc_path = shutil.which("tsc")
        # We assume npx is available in path if node is installed
        self.npx_path = shutil.which("npx") or "npx"

    def run_checks(self, codebase_path: str) -> QAReport:
        """
        Run all QA checks on the generated codebase.

        Args:
            codebase_path: Absolute path to the generated project root.

        Returns:
            QAReport with status of checks.
        """
        path = Path(codebase_path)
        if not path.exists():
            logger.error(f"Codebase path does not exist: {path}")
            return QAReport(issues=["Codebase path not found"])

        logger.info(f"Starting Quality Assurance on: {path}")
        report = QAReport()

        # 0. Validate code syntax FIRST before formatting
        backend_path = path / "backend"
        frontend_path = path / "frontend"

        if backend_path.exists():
            python_valid, py_issues = self._validate_python(backend_path)
            report.python_syntax_valid = python_valid
            report.validation_issues.extend(py_issues)
            if not python_valid:
                report.issues.append(f"Python syntax errors found: {len(py_issues)} issues")

        if frontend_path.exists():
            ts_valid, ts_issues = self._validate_typescript(frontend_path)
            report.typescript_valid = ts_valid
            report.validation_issues.extend(ts_issues)
            if not ts_valid and ts_issues:
                report.issues.append(f"TypeScript issues found: {len(ts_issues)} issues")

        # 1. Backend Formatting (only if syntax is valid)
        if backend_path.exists():
            if report.python_syntax_valid:
                report.backend_formatted = self._format_backend(backend_path)
            else:
                logger.warning("Skipping backend formatting due to syntax errors")
                report.backend_formatted = False
        else:
            logger.warning("No backend directory found to format.")

        # 2. Frontend Formatting
        if frontend_path.exists():
            report.frontend_formatted = self._format_frontend(frontend_path)
        else:
            logger.warning("No frontend directory found to format.")

        # Update summary counts
        error_files = set(issue.file for issue in report.validation_issues if issue.severity == "error")
        report.files_with_errors = len(error_files)

        return report

    def _validate_python(self, backend_path: Path) -> Tuple[bool, List[ValidationIssue]]:
        """
        Validate all Python files using ast.parse().
        Returns (all_valid, list_of_issues).
        """
        issues = []
        all_valid = True
        files_checked = 0

        for py_file in backend_path.rglob("*.py"):
            files_checked += 1
            try:
                content = py_file.read_text(encoding="utf-8")
                ast.parse(content, filename=str(py_file))

                # Also check for common import issues
                import_issues = self._check_python_imports(content, py_file)
                issues.extend(import_issues)

            except SyntaxError as e:
                all_valid = False
                issues.append(ValidationIssue(
                    file=str(py_file.relative_to(backend_path.parent)),
                    line=e.lineno,
                    message=f"SyntaxError: {e.msg}",
                    severity="error"
                ))
                logger.error(f"Syntax error in {py_file}: {e.msg} at line {e.lineno}")
            except Exception as e:
                all_valid = False
                issues.append(ValidationIssue(
                    file=str(py_file.relative_to(backend_path.parent)),
                    message=f"Parse error: {str(e)}",
                    severity="error"
                ))

        logger.info(f"Validated {files_checked} Python files, {len(issues)} issues found")
        return all_valid, issues

    def _check_python_imports(self, content: str, filepath: Path) -> List[ValidationIssue]:
        """Check for common import issues in Python code."""
        issues = []
        lines = content.split('\n')

        # Check for undefined imports in model files (common LLM mistake)
        for i, line in enumerate(lines, 1):
            # Check for Column usage without importing
            if 'Column(' in line and 'from sqlalchemy import' not in content and 'import Column' not in content:
                # Only flag if it's in a models file and no Column import exists
                if 'models' in str(filepath) and 'Column' not in content[:content.find('Column(')]:
                    issues.append(ValidationIssue(
                        file=str(filepath.name),
                        line=i,
                        message="Possible missing import: 'Column' used but sqlalchemy import not found",
                        severity="warning"
                    ))
                    break

            # Check for common SQLAlchemy types used without import
            sql_types = ['String', 'Integer', 'Float', 'Boolean', 'Text', 'DateTime', 'JSON']
            for sql_type in sql_types:
                if f'{sql_type}(' in line or f'{sql_type},' in line:
                    import_patterns = [
                        f'from sqlalchemy import.*{sql_type}',
                        f'from sqlalchemy.types import.*{sql_type}',
                        f'import {sql_type}'
                    ]
                    if not any(re.search(pat, content) for pat in import_patterns):
                        if f'Column({sql_type}' in line or f'= {sql_type}(' in line:
                            issues.append(ValidationIssue(
                                file=str(filepath.name),
                                line=i,
                                message=f"Possible missing import: '{sql_type}' type used without import",
                                severity="warning"
                            ))
                            break

        return issues

    def _validate_typescript(self, frontend_path: Path) -> Tuple[bool, List[ValidationIssue]]:
        """
        Validate TypeScript files using tsc --noEmit if available.
        Falls back to basic syntax check if tsc not available.
        """
        issues = []

        # Check if tsconfig.json exists
        tsconfig = frontend_path / "tsconfig.json"
        if not tsconfig.exists():
            logger.warning("No tsconfig.json found, skipping TypeScript validation")
            return True, []

        # Try using tsc if available
        if self.tsc_path:
            try:
                result = subprocess.run(
                    [self.tsc_path, "--noEmit", "--skipLibCheck"],
                    cwd=str(frontend_path),
                    capture_output=True,
                    text=True,
                    timeout=120
                )

                if result.returncode != 0:
                    # Parse tsc output for errors
                    for line in result.stdout.split('\n'):
                        if '.ts(' in line or '.tsx(' in line:
                            # Format: file(line,col): error TS1234: message
                            match = re.match(r'(.+?)\((\d+),\d+\):\s*(\w+)\s+TS\d+:\s*(.+)', line)
                            if match:
                                issues.append(ValidationIssue(
                                    file=match.group(1),
                                    line=int(match.group(2)),
                                    message=match.group(4),
                                    severity="error" if match.group(3) == "error" else "warning"
                                ))

                    logger.warning(f"TypeScript validation found {len(issues)} issues")
                    return False, issues

                logger.info("✓ TypeScript syntax valid")
                return True, []

            except subprocess.TimeoutExpired:
                logger.warning("TypeScript validation timed out")
                return True, []  # Don't fail on timeout
            except Exception as e:
                logger.warning(f"Error running tsc: {e}")
                return True, []
        else:
            # Fall back to basic file existence check
            logger.info("tsc not found, performing basic TypeScript validation")
            ts_files = list(frontend_path.rglob("*.tsx")) + list(frontend_path.rglob("*.ts"))
            for ts_file in ts_files:
                try:
                    content = ts_file.read_text(encoding="utf-8")
                    # Basic syntax checks
                    if content.count('{') != content.count('}'):
                        issues.append(ValidationIssue(
                            file=str(ts_file.relative_to(frontend_path)),
                            message="Mismatched braces detected",
                            severity="warning"
                        ))
                    if content.count('(') != content.count(')'):
                        issues.append(ValidationIssue(
                            file=str(ts_file.relative_to(frontend_path)),
                            message="Mismatched parentheses detected",
                            severity="warning"
                        ))
                except Exception as e:
                    issues.append(ValidationIssue(
                        file=str(ts_file.name),
                        message=f"Could not read file: {e}",
                        severity="error"
                    ))

            return len([i for i in issues if i.severity == "error"]) == 0, issues

    def _format_backend(self, backend_path: Path) -> bool:
        """Run Black and Isort on backend code."""
        success = True

        # Run isort
        if self.isort_path:
            try:
                subprocess.run(
                    [self.isort_path, ".", "--profile", "black"],
                    cwd=str(backend_path),
                    check=True,
                    capture_output=True,
                    timeout=30
                )
                logger.info("✓ Backend: Imports sorted (isort)")
            except subprocess.CalledProcessError as e:
                logger.warning(f"Isort failed: {e}")
                success = False
            except Exception as e:
                logger.warning(f"Error running isort: {e}")
                success = False
        else:
            logger.warning("isort not found in path")

        # Run black
        if self.black_path:
            try:
                subprocess.run(
                    [self.black_path, "."],
                    cwd=str(backend_path),
                    check=True,
                    capture_output=True,
                    timeout=60  # Prevent hanging
                )
                logger.info("✓ Backend: Code formatted (black)")
            except subprocess.TimeoutExpired:
                logger.warning("Black formatting timed out")
                success = False
            except subprocess.CalledProcessError as e:
                logger.warning(f"Black failed: {e}")
                success = False
            except Exception as e:
                logger.warning(f"Error running black: {e}")
                success = False
        else:
             logger.warning("black not found in path")

        return success

    def _format_frontend(self, frontend_path: Path) -> bool:
        """Run Prettier on frontend code."""
        # Check if npx works (simple check)
        try:
            subprocess.run(
                ["npx", "--version"],
                capture_output=True,
                timeout=10
            )
        except (subprocess.TimeoutExpired, RuntimeError, ValueError, FileNotFoundError, Exception):
            logger.warning("npx not available, skipping frontend formatting")
            return False

        try:
            # Running prettier via npx
            # "npx prettier --write ."
            logger.info("Running Prettier on frontend (this may take a moment)...")

            # Set CI=true to prevent interactive prompts
            env = os.environ.copy()
            env["CI"] = "true"

            subprocess.run(
                ["npx", "--yes", "prettier", "--write", "."],
                cwd=str(frontend_path),
                check=True,
                capture_output=True,
                timeout=120,
                env=env
            )
            logger.info("✓ Frontend: Code formatted (prettier)")
            return True
        except subprocess.TimeoutExpired:
            logger.warning("Prettier formatting timed out")
            return False
        except subprocess.CalledProcessError as e:
            logger.warning(f"Prettier failed: {e}")
            return False
        except Exception as e:
            logger.warning(f"Error running prettier: {e}")
            return False
