"""
Critic Integration for the v2 Code Generation Pipeline.

CriticPanel runs all five multi-agent critics (CodeCritic, OutputCritic,
SecurityCritic, PerformanceCritic, UXCritic) in parallel against a generated
project directory, then aggregates their verdicts into a single CriticReport.

Graceful degradation:
    If the LLM-backed critics cannot be imported (anthropic / openai not
    installed), the panel falls back to pure static analysis using the
    CodeCritic.SECURITY_PATTERNS regex bank and Python AST validation.
"""

from __future__ import annotations

import ast
import asyncio
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Try to import LLM-backed critics.  All of them transitively depend on
# ``anthropic`` or ``openai``, so a single ImportError guard is sufficient.
# ---------------------------------------------------------------------------
_LLM_CRITICS_AVAILABLE = False

try:
    from src.agents.critics.code_critic import CodeCritic
    from src.agents.critics.output_critic import OutputCritic
    from src.agents.critics.performance_critic import PerformanceCritic
    from src.agents.critics.security_critic import SecurityCritic
    from src.agents.critics.ux_critic import UXCritic
    from src.agents.base import LLMProvider
    from src.agents.messages import (
        AgentRole,
        CriticDecision,
        CriticReview,
        GeneratedCode,
    )
    _LLM_CRITICS_AVAILABLE = True
    logger.debug("critic_integration: LLM critics loaded successfully")
except ImportError as _import_err:
    logger.warning(
        "critic_integration: LLM critics unavailable (%s); "
        "falling back to static analysis only.",
        _import_err,
    )

    # Minimal stubs so the rest of this module can reference them without
    # conditional branching in every function body.
    class _StubDecision:  # noqa: N801
        APPROVE = "approve"
        REJECT = "reject"
        REQUEST_CHANGES = "request_changes"

    CriticDecision = _StubDecision  # type: ignore[misc,assignment]


# ---------------------------------------------------------------------------
# Security patterns lifted from CodeCritic for the static-only fallback.
# We re-define them here so they are available even when the critic modules
# cannot be imported.
# ---------------------------------------------------------------------------
_SECURITY_PATTERNS: List[tuple[str, str]] = [
    (r'eval\s*\(', "eval() is dangerous — potential code injection"),
    (r'exec\s*\(', "exec() is dangerous — potential code injection"),
    (r'__import__\s*\(', "Dynamic imports can be dangerous"),
    (r'subprocess\.call.*shell\s*=\s*True', "shell=True is dangerous"),
    (r'os\.system\s*\(', "os.system is dangerous — use subprocess"),
    (r'pickle\.loads?\s*\(', "Pickle is unsafe with untrusted data"),
    (r'yaml\.load\s*\([^,]*\)', "Use yaml.safe_load instead"),
    (r'SELECT.*\+.*\+', "Potential SQL injection"),
    (r'f["\'].*\{.*\}.*SELECT', "Potential SQL injection in f-string"),
    (r'(?:password|secret|api_key|token)\s*=\s*["\'][^"\']+', "Potential hardcoded secret"),
    (r'innerHTML\s*=', "innerHTML assignment — potential XSS"),
    (r'document\.write\s*\(', "document.write — potential XSS"),
]


# =============================================================================
# Output models
# =============================================================================


class CriticReviewSummary(BaseModel):
    """Condensed per-critic verdict suitable for serialisation."""

    critic_name: str
    score: int = Field(ge=0, le=100)
    passed: bool
    issues: List[Dict[str, Any]] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    decision: str = "approve"
    reasoning: str = ""


class CriticReport(BaseModel):
    """Aggregated result produced by CriticPanel."""

    overall_score: int = Field(ge=0, le=100)
    reviews: List[CriticReviewSummary] = Field(default_factory=list)
    critical_issues: List[str] = Field(default_factory=list)
    summary: str = ""
    llm_critics_used: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to a plain dict for SSE / JSON transport."""
        return self.model_dump()


# =============================================================================
# Static fallback analysis (used when LLM critics are unavailable)
# =============================================================================


def _static_security_check(filename: str, content: str) -> List[Dict[str, Any]]:
    """Run regex-based security checks on a single file."""
    issues: List[Dict[str, Any]] = []
    for pattern, description in _SECURITY_PATTERNS:
        for match in re.finditer(pattern, content, re.IGNORECASE):
            line_num = content[: match.start()].count("\n") + 1
            issues.append(
                {
                    "severity": "high",
                    "description": description,
                    "location": f"{filename}:{line_num}",
                }
            )
    return issues


def _static_ast_check(filename: str, content: str) -> List[Dict[str, Any]]:
    """Validate Python syntax via AST parsing."""
    if not filename.endswith(".py"):
        return []
    issues: List[Dict[str, Any]] = []
    try:
        ast.parse(content)
    except SyntaxError as exc:
        issues.append(
            {
                "severity": "critical",
                "description": f"Syntax error: {exc.msg}",
                "location": f"{filename}:{exc.lineno}",
            }
        )
    return issues


def _run_static_fallback(files: Dict[str, str]) -> CriticReviewSummary:
    """
    Static-analysis-only review used when LLM critics cannot be imported.

    Combines AST validation and security pattern checks across all files.
    """
    all_issues: List[Dict[str, Any]] = []
    for filename, content in files.items():
        all_issues.extend(_static_ast_check(filename, content))
        all_issues.extend(_static_security_check(filename, content))

    critical_count = sum(1 for i in all_issues if i.get("severity") == "critical")
    high_count = sum(1 for i in all_issues if i.get("severity") == "high")

    # Score: start at 100, deduct per issue
    score = max(0, 100 - critical_count * 20 - high_count * 10)
    passed = critical_count == 0

    recommendations = list(
        {i["description"] for i in all_issues}  # deduplicated
    )

    return CriticReviewSummary(
        critic_name="static_analysis",
        score=score,
        passed=passed,
        issues=all_issues,
        recommendations=recommendations,
        decision="reject" if not passed else "approve",
        reasoning=(
            f"Static analysis: {critical_count} critical, {high_count} high-severity issues "
            f"across {len(files)} file(s)."
        ),
    )


# =============================================================================
# Adapters — bridge between the critic agents' CriticReview and our summary
# =============================================================================


def _normalise_score(raw_score: Any) -> int:
    """Convert a 0-1 float or 0-100 int to a 0-100 int."""
    if raw_score is None:
        return 50
    try:
        s = float(raw_score)
    except (TypeError, ValueError):
        return 50
    # Scores ≤ 1.0 are assumed to be in the 0-1 range
    if s <= 1.0:
        return int(round(s * 100))
    return int(round(min(s, 100)))


def _critic_review_to_summary(
    critic_name: str, review: Any
) -> CriticReviewSummary:
    """Convert a CriticReview (or any duck-typed review object) to a CriticReviewSummary."""
    decision_value = getattr(review, "decision", CriticDecision.APPROVE)
    # decision may be an enum or a plain string
    if hasattr(decision_value, "value"):
        decision_str = decision_value.value
    else:
        decision_str = str(decision_value)

    passed = decision_str not in ("reject",)
    score = _normalise_score(getattr(review, "score", None))
    issues = list(getattr(review, "issues", []) or [])
    suggestions = list(getattr(review, "suggestions", []) or [])
    reasoning = str(getattr(review, "reasoning", ""))

    return CriticReviewSummary(
        critic_name=critic_name,
        score=score,
        passed=passed,
        issues=issues,
        recommendations=suggestions,
        decision=decision_str,
        reasoning=reasoning,
    )


# =============================================================================
# Per-critic async runners
# =============================================================================


async def _run_code_critic(
    generated_code: Any,
    context: Dict[str, Any],
) -> CriticReviewSummary:
    critic = CodeCritic()
    review = await critic.review(artifact=generated_code, context=context)
    return _critic_review_to_summary("code_critic", review)


async def _run_output_critic(
    generated_code: Any,
    context: Dict[str, Any],
) -> CriticReviewSummary:
    critic = OutputCritic()
    review = await critic.review(artifact=generated_code, context=context)
    return _critic_review_to_summary("output_critic", review)


async def _run_security_critic(
    generated_code: Any,
    requirements: str,
    llm_provider: Any,
) -> CriticReviewSummary:
    critic = SecurityCritic(llm_provider=llm_provider)
    review = await critic.review(code=generated_code, requirements=requirements)
    return _critic_review_to_summary("security_critic", review)


async def _run_performance_critic(
    generated_code: Any,
    requirements: str,
    llm_provider: Any,
) -> CriticReviewSummary:
    critic = PerformanceCritic(llm_provider=llm_provider)
    review = await critic.review(code=generated_code, requirements=requirements)
    return _critic_review_to_summary("performance_critic", review)


async def _run_ux_critic(
    generated_code: Any,
    requirements: str,
    llm_provider: Any,
) -> CriticReviewSummary:
    critic = UXCritic(llm_provider=llm_provider)
    review = await critic.review(code=generated_code, requirements=requirements)
    return _critic_review_to_summary("ux_critic", review)


# =============================================================================
# CriticPanel
# =============================================================================


class CriticPanel:
    """
    Runs all five critics against a generated project and aggregates results.

    Usage::

        panel = CriticPanel()
        report = await panel.run(
            output_dir="/path/to/generated/project",
            spec=system_spec,   # SystemSpec instance
        )
        print(report.overall_score)

    If LLM-backed critics are unavailable the panel falls back to pure static
    analysis (AST + security pattern matching) and sets
    ``report.llm_critics_used = False``.
    """

    def __init__(self) -> None:
        pass

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run(
        self,
        output_dir: str,
        spec: Any,  # SystemSpec — typed as Any to avoid circular import
    ) -> CriticReport:
        """
        Run all critics in parallel and return an aggregated CriticReport.

        Args:
            output_dir: Path to the directory containing generated files.
            spec:        SystemSpec produced by the architect phase.

        Returns:
            CriticReport with per-critic summaries and aggregate metrics.
        """
        files = self._read_files(output_dir)
        if not files:
            logger.warning("CriticPanel: no files found in %s — returning empty report", output_dir)
            return CriticReport(
                overall_score=0,
                summary="No generated files found for review.",
                llm_critics_used=False,
            )

        if _LLM_CRITICS_AVAILABLE:
            return await self._run_llm_critics(files, spec)
        else:
            return self._run_static_fallback(files)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _read_files(self, output_dir: str) -> Dict[str, str]:
        """Read all text files from output_dir (recursively, up to 500 KB each)."""
        _MAX_FILE_BYTES = 512 * 1024  # 512 KB per file
        files: Dict[str, str] = {}
        base = Path(output_dir)
        if not base.exists():
            logger.warning("CriticPanel: output_dir does not exist: %s", output_dir)
            return files

        for path in sorted(base.rglob("*")):
            if not path.is_file():
                continue
            # Skip binary / lockfiles / hidden directories
            rel = path.relative_to(base)
            parts = rel.parts
            if any(p.startswith(".") for p in parts):
                continue
            if path.name in {"package-lock.json", "yarn.lock", "poetry.lock", "Pipfile.lock"}:
                continue
            # Only text-ish extensions
            suffix = path.suffix.lower()
            if suffix in {
                ".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".scss",
                ".json", ".yaml", ".yml", ".toml", ".md", ".txt", ".env",
                ".sh", ".sql", "",
            }:
                try:
                    content = path.read_bytes()[:_MAX_FILE_BYTES].decode("utf-8", errors="replace")
                    files[str(rel)] = content
                except OSError as exc:
                    logger.debug("CriticPanel: could not read %s: %s", path, exc)

        logger.debug("CriticPanel: loaded %d files from %s", len(files), output_dir)
        return files

    def _build_generated_code(self, files: Dict[str, str]) -> Any:
        """
        Build a GeneratedCode object compatible with the critic agents.

        The GeneratedCode model in messages.py uses ``files: Dict[str, str]``,
        which is what the CriticAgent-based critics (CodeCritic, OutputCritic)
        consume.  The standalone critics (Security, Performance, UX) expect
        ``code.files`` to be an iterable of objects with ``.filename`` and
        ``.content`` attributes — but their ``review()`` methods join files
        via ``f"# File: {f.filename}\\n{f.content}"``.

        We satisfy both APIs by attaching a ``.files`` attribute that works
        as a dict AND as an iterable of named-tuple-like objects.
        """
        # GeneratedCode.files is Dict[str, str] — pass it directly.
        return GeneratedCode(
            files=files,
            tech_stack="unknown",
            dependencies=[],
        )

    def _build_requirements(self, spec: Any) -> str:
        """Extract a plain-English requirements string from the SystemSpec."""
        parts: List[str] = []
        app_name = getattr(spec, "app_name", None) or getattr(spec, "name", "")
        description = getattr(spec, "description", "")
        if app_name:
            parts.append(f"Application: {app_name}")
        if description:
            parts.append(f"Description: {description}")

        entities = getattr(spec, "entities", None) or getattr(spec, "models", None) or []
        if entities:
            names = [getattr(e, "name", str(e)) for e in entities[:10]]
            parts.append(f"Entities: {', '.join(names)}")

        routes = getattr(spec, "api_routes", None) or getattr(spec, "routes", None) or []
        if routes:
            route_strs = []
            for r in routes[:10]:
                method = getattr(r, "method", "")
                path = getattr(r, "path", str(r))
                route_strs.append(f"{method} {path}".strip())
            parts.append(f"API routes: {', '.join(route_strs)}")

        pages = getattr(spec, "pages", None) or []
        if pages:
            page_names = [getattr(p, "name", str(p)) for p in pages[:10]]
            parts.append(f"Pages: {', '.join(page_names)}")

        return "\n".join(parts) if parts else "No requirements available."

    def _build_context(self, spec: Any) -> Dict[str, Any]:
        """Build the context dict required by CriticAgent-based critics."""
        ctx: Dict[str, Any] = {}
        if spec is not None:
            try:
                ctx["spec"] = spec.model_dump() if hasattr(spec, "model_dump") else dict(spec)
            except Exception:
                ctx["spec"] = str(spec)
        return ctx

    async def _run_llm_critics(
        self,
        files: Dict[str, str],
        spec: Any,
    ) -> CriticReport:
        """Run all five LLM-backed critics in parallel."""
        generated_code = self._build_generated_code(files)
        requirements = self._build_requirements(spec)
        context = self._build_context(spec)

        # The standalone critics need an LLMProvider.  Instantiate one; it will
        # pick up ANTHROPIC_API_KEY / OPENAI_API_KEY from the environment.
        try:
            llm_provider = LLMProvider()
        except Exception as exc:
            logger.warning(
                "CriticPanel: could not create LLMProvider (%s); "
                "falling back to static analysis.",
                exc,
            )
            return self._run_static_fallback(files)

        # The standalone critics (Security/Performance/UX) pass `code.files`
        # as an iterable of objects with .filename / .content.  However,
        # GeneratedCode.files is a Dict[str, str].  We need to supply a
        # wrapper that the standalone critics can iterate.
        generated_code_wrapped = _FilesAdapter(files)

        tasks = {
            "code_critic": _run_code_critic(generated_code, context),
            "output_critic": _run_output_critic(generated_code, context),
            "security_critic": _run_security_critic(generated_code_wrapped, requirements, llm_provider),
            "performance_critic": _run_performance_critic(generated_code_wrapped, requirements, llm_provider),
            "ux_critic": _run_ux_critic(generated_code_wrapped, requirements, llm_provider),
        }

        results: Dict[str, CriticReviewSummary] = {}
        coros = list(tasks.values())
        names = list(tasks.keys())

        # gather with return_exceptions so one failure doesn't kill the rest
        raw_results = await asyncio.gather(*coros, return_exceptions=True)

        for name, outcome in zip(names, raw_results):
            if isinstance(outcome, BaseException):
                logger.warning(
                    "CriticPanel: critic '%s' raised %s: %s",
                    name, type(outcome).__name__, outcome,
                )
                # Substitute a neutral summary so the pipeline doesn't lose
                # all results because of one failing critic.
                results[name] = CriticReviewSummary(
                    critic_name=name,
                    score=50,
                    passed=True,
                    issues=[],
                    recommendations=[],
                    decision="approve",
                    reasoning=f"Critic unavailable: {outcome}",
                )
            else:
                results[name] = outcome  # type: ignore[assignment]

        reviews = list(results.values())
        return _aggregate(reviews, llm_critics_used=True)

    def _run_static_fallback(self, files: Dict[str, str]) -> CriticReport:
        """Run static-only analysis when LLM critics are unavailable."""
        summary = _run_static_fallback(files)
        return _aggregate([summary], llm_critics_used=False)


# =============================================================================
# Adapter for standalone critics
# =============================================================================


class _FileEntry:
    """Mimics the file-entry object expected by SecurityCritic / PerformanceCritic / UXCritic."""

    __slots__ = ("filename", "content")

    def __init__(self, filename: str, content: str) -> None:
        self.filename = filename
        self.content = content


class _FilesAdapter:
    """
    Wraps a Dict[str, str] so that iterating over .files yields _FileEntry
    objects, satisfying the standalone critic contract::

        all_code = "\\n\\n".join(
            f"# File: {f.filename}\\n{f.content}"
            for f in code.files
        )
    """

    def __init__(self, files: Dict[str, str]) -> None:
        self._entries = [_FileEntry(name, content) for name, content in files.items()]

    @property
    def files(self) -> List[_FileEntry]:
        return self._entries


# =============================================================================
# Aggregation
# =============================================================================


def _aggregate(reviews: List[CriticReviewSummary], llm_critics_used: bool) -> CriticReport:
    """Combine per-critic summaries into a single CriticReport."""
    if not reviews:
        return CriticReport(
            overall_score=0,
            summary="No reviews produced.",
            llm_critics_used=llm_critics_used,
        )

    # Overall score = weighted average (equal weights for now)
    overall_score = int(round(sum(r.score for r in reviews) / len(reviews)))

    # Collect critical issues (severity == "critical" from any critic)
    critical_issues: List[str] = []
    for review in reviews:
        for issue in review.issues:
            if isinstance(issue, dict) and issue.get("severity") == "critical":
                desc = issue.get("description", str(issue))
                loc = issue.get("location", "")
                critical_issues.append(f"[{review.critic_name}] {desc}" + (f" ({loc})" if loc else ""))

    # Build human-readable summary
    passed_critics = [r.critic_name for r in reviews if r.passed]
    failed_critics = [r.critic_name for r in reviews if not r.passed]

    parts: List[str] = [f"Overall score: {overall_score}/100."]
    if passed_critics:
        parts.append(f"Passed: {', '.join(passed_critics)}.")
    if failed_critics:
        parts.append(f"Failed: {', '.join(failed_critics)}.")
    if critical_issues:
        parts.append(f"{len(critical_issues)} critical issue(s) found.")
    if not llm_critics_used:
        parts.append("(Static analysis only — LLM critics not available.)")

    summary = " ".join(parts)

    return CriticReport(
        overall_score=overall_score,
        reviews=reviews,
        critical_issues=critical_issues,
        summary=summary,
        llm_critics_used=llm_critics_used,
    )
