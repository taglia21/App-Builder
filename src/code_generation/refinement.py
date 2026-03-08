"""
Iterative Refinement Engine for Ignara App-Builder.

Allows users to describe changes to their generated codebase in natural language.
The engine analyzes the instruction, determines which files to modify, generates
new file content via LLM, validates the changes, applies them, and records a
history entry so changes can be undone.
"""

from __future__ import annotations

import ast
import asyncio
import json
import logging
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field

from src.llm.client import get_llm_client

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Directories / file patterns to skip when building the project tree
_IGNORED_DIRS: frozenset[str] = frozenset(
    {
        ".git",
        "__pycache__",
        ".next",
        "node_modules",
        ".ignara_backups",
        "dist",
        "build",
        ".venv",
        "venv",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
    }
)

_IGNORED_EXTENSIONS: frozenset[str] = frozenset(
    {".pyc", ".pyo", ".pyd", ".so", ".dll", ".exe", ".bin", ".lock"}
)

# Maximum number of characters to include per file when sending context to LLM
_MAX_FILE_CHARS: int = 12_000

# Backup directory name (relative to project root)
_BACKUP_DIR = ".ignara_backups"

# Scope keyword maps for auto-detection
_BACKEND_KEYWORDS: list[str] = [
    "endpoint",
    "route",
    "api",
    "model",
    "schema",
    "migration",
    "database",
    "db",
    "middleware",
    "authentication",
    "auth",
    "backend",
    "fastapi",
    "sqlalchemy",
    "alembic",
    "service",
    "celery",
    "worker",
    "email notification",
    "webhook",
    "cron",
    "background task",
    "permission",
    "role",
]

_FRONTEND_KEYWORDS: list[str] = [
    "page",
    "component",
    "ui",
    "button",
    "form",
    "chart",
    "dashboard",
    "navigation",
    "nav",
    "menu",
    "sidebar",
    "modal",
    "color scheme",
    "theme",
    "style",
    "css",
    "tailwind",
    "frontend",
    "react",
    "next.js",
    "typescript",
    "display",
    "show",
    "render",
    "layout",
    "responsive",
]


# ---------------------------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------------------------


class FileChange(BaseModel):
    """Represents a single file change within a refinement operation."""

    path: str = Field(..., description="Relative path from project root")
    change_type: str = Field(
        ..., description="One of 'modified', 'created', or 'deleted'"
    )
    diff_summary: str = Field(
        ..., description="Human-readable description of what changed in this file"
    )
    before_lines: Optional[int] = Field(
        None, description="Line count before the change (None for new files)"
    )
    after_lines: Optional[int] = Field(
        None, description="Line count after the change (None for deleted files)"
    )


class RefinementRequest(BaseModel):
    """Describes a user's natural-language request to change the generated codebase."""

    instruction: str = Field(
        ...,
        description=(
            "Natural language description of the desired change, e.g. "
            "'Add a rating field to products' or 'Make the dashboard show a chart'."
        ),
    )
    project_path: str = Field(
        ..., description="Absolute or relative path to the generated project root"
    )
    scope: Optional[str] = Field(
        None,
        description=(
            "Restrict changes to 'backend', 'frontend', 'full', or None to auto-detect"
        ),
    )
    context: Optional[dict[str, Any]] = Field(
        None,
        description=(
            "Additional context such as the original SystemSpec. "
            "Helps the LLM understand what was already built."
        ),
    )


class RefinementResult(BaseModel):
    """The outcome of applying a single refinement to a project."""

    files_modified: list[FileChange] = Field(
        default_factory=list, description="Files that were updated in-place"
    )
    files_created: list[FileChange] = Field(
        default_factory=list, description="New files that were added to the project"
    )
    files_deleted: list[FileChange] = Field(
        default_factory=list, description="Files that were removed"
    )
    explanation: str = Field(
        ..., description="LLM summary of what was changed and why"
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Non-fatal issues encountered during refinement",
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _count_lines(text: str) -> int:
    """Return the number of lines in *text* (0 for empty string)."""
    if not text:
        return 0
    return text.count("\n") + (0 if text.endswith("\n") else 1)


def _validate_python(source: str, path: str) -> Optional[str]:
    """
    Attempt to parse *source* as Python.

    Returns an error message string on failure, or None if the source is valid.
    """
    try:
        ast.parse(source)
        return None
    except SyntaxError as exc:
        return f"Python syntax error in {path}: {exc}"


def _validate_typescript(source: str, path: str) -> Optional[str]:
    """
    Very basic structural check for TypeScript / JavaScript files.

    Returns an error message string if something looks obviously wrong, else None.
    """
    # Count braces/brackets to catch catastrophic mismatches
    open_braces = source.count("{")
    close_braces = source.count("}")
    if abs(open_braces - close_braces) > 5:  # allow some tolerance
        return (
            f"Brace mismatch in {path}: "
            f"{open_braces} opening vs {close_braces} closing braces"
        )
    return None


def _extract_json_block(text: str) -> Optional[str]:
    """
    Extract the first JSON object or array from *text*.

    The LLM often wraps JSON in markdown code fences; this handles that.
    """
    # Try JSON code fence first
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", text, re.DOTALL)
    if fence_match:
        return fence_match.group(1)

    # Try to find a raw JSON object
    obj_match = re.search(r"(\{.*\})", text, re.DOTALL)
    if obj_match:
        return obj_match.group(1)

    return None


def _extract_code_block(text: str) -> str:
    """
    Strip markdown code fences from LLM output to get raw source code.

    If no fences are present the text is returned as-is.
    """
    # Remove leading/trailing ``` fences (with optional language tag)
    stripped = re.sub(r"^```[^\n]*\n", "", text.strip())
    stripped = re.sub(r"\n```$", "", stripped)
    return stripped.strip()


# ---------------------------------------------------------------------------
# RefinementEngine
# ---------------------------------------------------------------------------


class RefinementEngine:
    """
    Applies natural-language change instructions to a generated project.

    Workflow
    --------
    1. Detect scope (backend / frontend / full) if not supplied.
    2. Build project tree and send it to the LLM to get a *change plan*
       (JSON describing which files to touch and how).
    3. For every file in the plan, read the current content, gather related
       files as context, and ask the LLM for the complete new file content.
    4. Validate generated content (AST for Python, brace-check for TS).
    5. Back up originals to `.ignara_backups/<timestamp>/`.
    6. Write all changes atomically.
    7. Return a :class:`RefinementResult` describing what changed.
    """

    def __init__(self) -> None:
        self._client = get_llm_client("auto")
        self._history = RefinementHistory()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def refine(self, request: RefinementRequest) -> RefinementResult:
        """
        Apply *request.instruction* to the project at *request.project_path*.

        Returns a :class:`RefinementResult` describing all changes made.
        """
        project_path = os.path.abspath(request.project_path)
        if not os.path.isdir(project_path):
            raise ValueError(
                f"project_path does not exist or is not a directory: {project_path}"
            )

        logger.info(
            "Starting refinement | project=%s | instruction=%r",
            project_path,
            request.instruction[:120],
        )

        # 1. Detect / normalise scope
        scope = request.scope or self._detect_scope(request.instruction)
        logger.debug("Resolved scope: %s", scope)

        # 2. Build project tree for LLM context
        tree = self._get_project_tree(project_path, scope=scope)

        # 3. Ask LLM for a change plan
        change_plan = await self._plan_changes(
            instruction=request.instruction,
            project_path=project_path,
            tree=tree,
            scope=scope,
            context=request.context,
        )
        if not change_plan:
            logger.warning("LLM returned an empty change plan.")
            return RefinementResult(
                explanation="No changes were identified for this instruction.",
                warnings=["LLM returned an empty change plan."],
            )

        logger.info(
            "Change plan received: %d file(s) to touch",
            len(change_plan.get("files", [])),
        )

        # 4. Generate new content for each file
        pending_writes: dict[str, str] = {}   # path -> new content
        pending_deletes: list[str] = []
        file_changes: dict[str, FileChange] = {}
        warnings: list[str] = []

        for file_spec in change_plan.get("files", []):
            rel_path: str = file_spec.get("path", "").strip("/")
            action: str = file_spec.get("action", "modify").lower()
            reason: str = file_spec.get("reason", "")

            abs_path = os.path.join(project_path, rel_path)

            if action == "delete":
                pending_deletes.append(abs_path)
                file_changes[rel_path] = FileChange(
                    path=rel_path,
                    change_type="deleted",
                    diff_summary=reason or "File removed as part of refinement",
                    before_lines=(
                        _count_lines(self._read_file(abs_path))
                        if os.path.isfile(abs_path)
                        else None
                    ),
                    after_lines=None,
                )
                continue

            # Determine if this is a new file
            is_new = not os.path.isfile(abs_path)
            change_type = "created" if is_new else "modified"

            # Read current content (empty string for new files)
            current_content = "" if is_new else self._read_file(abs_path)

            # Read related files for richer context
            related: dict[str, str] = {}
            if not is_new:
                related = self._get_related_files(
                    project_path=project_path,
                    target_file=rel_path,
                )

            # Generate new content via LLM
            new_content = await self._generate_file_content(
                instruction=request.instruction,
                file_spec=file_spec,
                current_content=current_content,
                related_files=related,
                project_path=project_path,
            )

            if new_content is None:
                warnings.append(
                    f"Could not generate content for {rel_path}; skipping."
                )
                continue

            # Validate
            validation_error = self._validate_content(new_content, rel_path)
            if validation_error:
                warnings.append(validation_error)
                logger.warning("Validation warning: %s", validation_error)
                # We still proceed but warn the user

            pending_writes[abs_path] = new_content
            file_changes[rel_path] = FileChange(
                path=rel_path,
                change_type=change_type,
                diff_summary=reason or f"{change_type.capitalize()} as part of refinement",
                before_lines=_count_lines(current_content) if not is_new else None,
                after_lines=_count_lines(new_content),
            )

        if not pending_writes and not pending_deletes:
            return RefinementResult(
                explanation=change_plan.get("explanation", "No actionable changes produced."),
                warnings=warnings + ["No file content was generated."],
            )

        # 5. Back up originals
        files_to_backup = list(pending_writes.keys()) + pending_deletes
        backup_dir = await asyncio.to_thread(
            self._backup_files,
            project_path,
            files_to_backup,
        )
        logger.info("Backed up originals to: %s", backup_dir)

        # 6. Apply changes
        await asyncio.to_thread(
            self._apply_changes, pending_writes, pending_deletes
        )
        logger.info(
            "Applied %d write(s) and %d delete(s)",
            len(pending_writes),
            len(pending_deletes),
        )

        # 7. Build result
        modified = [
            fc for fc in file_changes.values() if fc.change_type == "modified"
        ]
        created = [
            fc for fc in file_changes.values() if fc.change_type == "created"
        ]
        deleted = [
            fc for fc in file_changes.values() if fc.change_type == "deleted"
        ]

        result = RefinementResult(
            files_modified=modified,
            files_created=created,
            files_deleted=deleted,
            explanation=change_plan.get(
                "explanation", "Refinement applied successfully."
            ),
            warnings=warnings,
        )

        # 8. Record in history
        self._history.add(request, result)

        return result

    # ------------------------------------------------------------------
    # LLM interaction helpers
    # ------------------------------------------------------------------

    async def _plan_changes(
        self,
        instruction: str,
        project_path: str,
        tree: str,
        scope: str,
        context: Optional[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Ask the LLM which files need to change, created, or deleted.

        Returns a dict with keys:
            - ``files``: list of {path, action, reason, guidance}
            - ``explanation``: summary of the overall change
        """
        context_snippet = ""
        if context:
            context_snippet = (
                "\n\nAdditional context about the project specification:\n"
                + json.dumps(context, indent=2)[:3000]
            )

        system_prompt = (
            "You are an expert software architect. "
            "You analyse project file trees and determine the minimal set of changes "
            "needed to satisfy a user's refinement instruction. "
            "Always respond with valid JSON only — no prose outside the JSON block."
        )

        user_prompt = f"""Given the following project file tree for a generated application:

<file_tree>
{tree}
</file_tree>
{context_snippet}

The user wants to make this change (scope: {scope}):
"{instruction}"

Analyse the change carefully. Consider:
- Direct files that must be modified (models, schemas, routes, components, etc.)
- Cascading changes required (e.g. if a model changes, its schema and migrations may too)
- New files that must be created (new pages, services, utilities, etc.)
- Any files that should be removed

Return a JSON object in EXACTLY this format:
{{
  "explanation": "<one-paragraph summary of what will be changed and why>",
  "files": [
    {{
      "path": "<relative path from project root>",
      "action": "<modify | create | delete>",
      "reason": "<why this file needs to change>",
      "guidance": "<specific instructions for what to change in this file>"
    }}
  ]
}}

Only include files that genuinely need to change. Limit to the most impactful changes.
"""

        raw = await asyncio.to_thread(
            self._client.complete,
            user_prompt,
            system_prompt,
            4096,
            0.3,
            False,
        )

        try:
            json_str = _extract_json_block(raw.content)
            if json_str:
                return json.loads(json_str)
        except (json.JSONDecodeError, AttributeError) as exc:
            logger.error("Failed to parse change plan JSON: %s | raw=%r", exc, raw.content[:500])

        return {}

    async def _generate_file_content(
        self,
        instruction: str,
        file_spec: dict[str, Any],
        current_content: str,
        related_files: dict[str, str],
        project_path: str,
    ) -> Optional[str]:
        """
        Generate the complete new content for a single file.

        Returns the new file content as a string, or None on failure.
        """
        rel_path: str = file_spec.get("path", "unknown")
        guidance: str = file_spec.get("guidance", "")
        action: str = file_spec.get("action", "modify")
        is_new = action == "create"

        # Build related-files context snippet
        related_snippet = ""
        if related_files:
            parts = []
            for rpath, rcontent in list(related_files.items())[:4]:
                truncated = rcontent[:2000] + ("..." if len(rcontent) > 2000 else "")
                parts.append(f"--- {rpath} ---\n{truncated}")
            related_snippet = "\n\nRelated files for context:\n" + "\n\n".join(parts)

        current_section = ""
        if not is_new and current_content:
            truncated_current = (
                current_content[:_MAX_FILE_CHARS]
                + ("...(truncated)" if len(current_content) > _MAX_FILE_CHARS else "")
            )
            current_section = f"\n\nCURRENT FILE CONTENT ({rel_path}):\n```\n{truncated_current}\n```"

        system_prompt = (
            "You are an expert full-stack developer. "
            "When asked to modify or create a file, you return ONLY the complete new file "
            "content — no explanations, no markdown prose, no ``` fences wrapping the "
            "entire response (you may use fences inside docstrings if they appear in the "
            "original). The output must be the raw file text ready to write to disk."
        )

        verb = "Create" if is_new else "Update"
        user_prompt = f"""{verb} the file `{rel_path}` as part of this user instruction:
"{instruction}"

Specific guidance for this file:
{guidance or "(Apply changes as needed based on the instruction.)"}
{current_section}{related_snippet}

Return ONLY the complete new file content. Do not include any commentary before or after the code.
"""

        try:
            raw = await asyncio.to_thread(
                self._client.complete,
                user_prompt,
                system_prompt,
                4096,
                0.3,
                False,
            )
            content = _extract_code_block(raw.content)
            if not content.strip():
                logger.warning("LLM returned empty content for %s", rel_path)
                return None
            return content
        except Exception as exc:
            logger.error("Error generating content for %s: %s", rel_path, exc)
            return None

    # ------------------------------------------------------------------
    # Utility methods
    # ------------------------------------------------------------------

    def _get_project_tree(
        self, project_path: str, scope: Optional[str] = None, max_files: int = 200
    ) -> str:
        """
        Return a formatted, indented file tree for the given project path.

        Parameters
        ----------
        project_path:
            Root directory of the generated project.
        scope:
            Optional scope filter.  When ``"backend"`` only backend/ files
            are shown; when ``"frontend"`` only frontend/ files; otherwise all.
        max_files:
            Hard cap on the number of lines in the tree to avoid huge prompts.
        """
        lines: list[str] = []

        def _walk(directory: str, prefix: str, count: list[int]) -> None:
            if count[0] >= max_files:
                return
            try:
                entries = sorted(os.scandir(directory), key=lambda e: (e.is_file(), e.name))
            except PermissionError:
                return

            for entry in entries:
                if count[0] >= max_files:
                    lines.append(f"{prefix}... (truncated)")
                    return
                if entry.name in _IGNORED_DIRS:
                    continue
                ext = os.path.splitext(entry.name)[1].lower()
                if ext in _IGNORED_EXTENSIONS:
                    continue

                rel = os.path.relpath(entry.path, project_path)

                # Apply scope filter at the top level
                if scope in ("backend",) and not rel.startswith("backend"):
                    # Still include root-level config files
                    if entry.is_dir():
                        continue
                elif scope in ("frontend",) and not rel.startswith("frontend"):
                    if entry.is_dir():
                        continue

                if entry.is_dir():
                    lines.append(f"{prefix}{entry.name}/")
                    count[0] += 1
                    _walk(entry.path, prefix + "  ", count)
                else:
                    lines.append(f"{prefix}{entry.name}")
                    count[0] += 1

        _walk(project_path, "", [0])
        return "\n".join(lines) if lines else "(empty project)"

    def _read_file(self, path: str) -> str:
        """
        Read and return the content of a file.

        Returns an empty string if the file does not exist or cannot be read.
        """
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                return fh.read()
        except OSError as exc:
            logger.debug("Could not read %s: %s", path, exc)
            return ""

    def _get_related_files(
        self, project_path: str, target_file: str
    ) -> dict[str, str]:
        """
        Return a dict of {relative_path: content} for files related to *target_file*.

        Heuristics
        ----------
        - Python model file → also read its matching schema.py and router/routes.py
        - Next.js page → also read types.ts, api.ts in the same directory
        - Any file → also read the closest __init__.py or index.ts
        """
        related: dict[str, str] = {}
        base = os.path.dirname(target_file)
        name = os.path.splitext(os.path.basename(target_file))[0]
        ext = os.path.splitext(target_file)[1]

        candidates: list[str] = []

        if ext == ".py":
            # Common sibling patterns in FastAPI projects
            siblings = ["schemas.py", "models.py", "routes.py", "router.py",
                        "service.py", "deps.py", "__init__.py"]
            for sib in siblings:
                candidates.append(os.path.join(base, sib))
            # A schema file might have the same stem with "schema" in the name
            candidates.append(os.path.join(base, f"{name}_schema.py"))
            candidates.append(os.path.join(base, f"{name}s.py"))

        elif ext in (".ts", ".tsx"):
            siblings = ["types.ts", "api.ts", "index.ts", "hooks.ts", "utils.ts"]
            for sib in siblings:
                candidates.append(os.path.join(base, sib))
            candidates.append(os.path.join(base, f"{name}.types.ts"))

        # Always try the parent __init__ / index
        parent = os.path.dirname(base)
        candidates.append(os.path.join(parent, "__init__.py"))
        candidates.append(os.path.join(parent, "index.ts"))

        for cand in candidates:
            abs_cand = os.path.join(project_path, cand)
            rel_cand = os.path.relpath(abs_cand, project_path)
            if (
                rel_cand != target_file
                and os.path.isfile(abs_cand)
                and rel_cand not in related
            ):
                content = self._read_file(abs_cand)
                if content:
                    related[rel_cand] = content

        return related

    def _detect_scope(self, instruction: str) -> str:
        """
        Infer whether the change affects 'backend', 'frontend', or 'full'.

        Scores the instruction against keyword lists and picks the higher score.
        Returns 'full' on a tie or when both sides score above a threshold.
        """
        lower = instruction.lower()

        backend_score = sum(1 for kw in _BACKEND_KEYWORDS if kw in lower)
        frontend_score = sum(1 for kw in _FRONTEND_KEYWORDS if kw in lower)

        logger.debug(
            "Scope detection — backend_score=%d, frontend_score=%d",
            backend_score,
            frontend_score,
        )

        if backend_score == 0 and frontend_score == 0:
            return "full"
        if backend_score > 0 and frontend_score > 0:
            return "full"
        if backend_score > frontend_score:
            return "backend"
        return "frontend"

    def _validate_content(self, content: str, rel_path: str) -> Optional[str]:
        """
        Run static validation on generated file content.

        Returns an error/warning message or None if content looks valid.
        """
        ext = os.path.splitext(rel_path)[1].lower()
        if ext == ".py":
            return _validate_python(content, rel_path)
        if ext in (".ts", ".tsx", ".js", ".jsx"):
            return _validate_typescript(content, rel_path)
        return None

    # ------------------------------------------------------------------
    # File system helpers
    # ------------------------------------------------------------------

    def _backup_files(
        self, project_path: str, abs_paths: list[str]
    ) -> str:
        """
        Copy the given files into a timestamped backup directory.

        Returns the absolute path to the backup directory created.
        """
        timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup_root = os.path.join(project_path, _BACKUP_DIR, timestamp)
        os.makedirs(backup_root, exist_ok=True)

        for abs_src in abs_paths:
            if not os.path.isfile(abs_src):
                continue
            rel = os.path.relpath(abs_src, project_path)
            dest = os.path.join(backup_root, rel)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copy2(abs_src, dest)
            logger.debug("Backed up %s → %s", rel, dest)

        return backup_root

    @staticmethod
    def _apply_changes(
        writes: dict[str, str],
        deletes: list[str],
    ) -> None:
        """
        Write new file contents and delete files as specified.

        All writes happen before any deletes so the codebase remains coherent
        in the event of a partial failure.
        """
        for abs_path, content in writes.items():
            os.makedirs(os.path.dirname(abs_path), exist_ok=True)
            with open(abs_path, "w", encoding="utf-8") as fh:
                fh.write(content)
            logger.debug("Wrote %s (%d chars)", abs_path, len(content))

        for abs_path in deletes:
            try:
                os.remove(abs_path)
                logger.debug("Deleted %s", abs_path)
            except FileNotFoundError:
                logger.debug("File already absent, skip delete: %s", abs_path)


# ---------------------------------------------------------------------------
# RefinementHistory
# ---------------------------------------------------------------------------


class _HistoryEntry(BaseModel):
    """A single recorded refinement event."""

    timestamp: str = Field(
        default_factory=lambda: datetime.now(tz=timezone.utc).isoformat()
    )
    project_path: str
    instruction: str
    scope: Optional[str]
    files_modified: list[str]
    files_created: list[str]
    files_deleted: list[str]
    explanation: str
    warnings: list[str]
    backup_dir: Optional[str] = None


class RefinementHistory:
    """
    Tracks all refinements applied to projects and supports undo.

    History is persisted as a JSON file inside the project's backup directory
    so it survives process restarts.

    File layout
    -----------
    ``<project_path>/.ignara_backups/history.json``
    """

    _HISTORY_FILENAME = "history.json"

    def add(self, request: RefinementRequest, result: RefinementResult) -> None:
        """
        Record a completed refinement in the project's history file.
        """
        project_path = os.path.abspath(request.project_path)
        entry = _HistoryEntry(
            project_path=project_path,
            instruction=request.instruction,
            scope=request.scope,
            files_modified=[fc.path for fc in result.files_modified],
            files_created=[fc.path for fc in result.files_created],
            files_deleted=[fc.path for fc in result.files_deleted],
            explanation=result.explanation,
            warnings=result.warnings,
            backup_dir=self._latest_backup_dir(project_path),
        )

        history = self._load_history(project_path)
        history.append(entry.model_dump())
        self._save_history(project_path, history)
        logger.debug(
            "Recorded refinement history entry for project=%s", project_path
        )

    def get_history(self, project_path: str) -> list[dict[str, Any]]:
        """
        Return the list of past refinement entries for *project_path*.

        Each element is a dictionary matching the :class:`_HistoryEntry` schema.
        """
        project_path = os.path.abspath(project_path)
        return self._load_history(project_path)

    def undo_last(self, project_path: str) -> Optional[dict[str, Any]]:
        """
        Revert the most recent refinement by restoring backed-up files.

        Returns the reverted history entry dict, or None if there is nothing
        to undo or the backup directory cannot be found.
        """
        project_path = os.path.abspath(project_path)
        history = self._load_history(project_path)

        if not history:
            logger.info("No history entries found for project=%s", project_path)
            return None

        last_entry = history[-1]
        backup_dir: Optional[str] = last_entry.get("backup_dir")

        if not backup_dir or not os.path.isdir(backup_dir):
            logger.warning(
                "Backup directory not found for undo: %s", backup_dir
            )
            return None

        restored_count = 0
        failed: list[str] = []

        # Restore modified / deleted files from backup
        for rel_path in (
            last_entry.get("files_modified", [])
            + last_entry.get("files_deleted", [])
        ):
            backup_src = os.path.join(backup_dir, rel_path)
            if not os.path.isfile(backup_src):
                logger.debug("No backup for %s, skipping restore", rel_path)
                continue
            dest = os.path.join(project_path, rel_path)
            try:
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                shutil.copy2(backup_src, dest)
                restored_count += 1
                logger.debug("Restored %s from backup", rel_path)
            except OSError as exc:
                failed.append(f"{rel_path}: {exc}")

        # Remove newly created files (they won't exist in the backup)
        for rel_path in last_entry.get("files_created", []):
            abs_path = os.path.join(project_path, rel_path)
            if os.path.isfile(abs_path):
                try:
                    os.remove(abs_path)
                    logger.debug("Removed created file during undo: %s", rel_path)
                except OSError as exc:
                    failed.append(f"{rel_path} (delete): {exc}")

        if failed:
            logger.warning("Undo completed with errors: %s", failed)

        # Pop the last entry from history
        history.pop()
        self._save_history(project_path, history)

        logger.info(
            "Undo complete: restored %d file(s) for project=%s",
            restored_count,
            project_path,
        )
        return last_entry

    # ------------------------------------------------------------------
    # Internal persistence helpers
    # ------------------------------------------------------------------

    @classmethod
    def _history_path(cls, project_path: str) -> str:
        return os.path.join(project_path, _BACKUP_DIR, cls._HISTORY_FILENAME)

    @classmethod
    def _load_history(cls, project_path: str) -> list[dict[str, Any]]:
        path = cls._history_path(project_path)
        if not os.path.isfile(path):
            return []
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, list):
                return data
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Could not load refinement history: %s", exc)
        return []

    @classmethod
    def _save_history(cls, project_path: str, history: list[dict[str, Any]]) -> None:
        path = cls._history_path(project_path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        try:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(history, fh, indent=2, default=str)
        except OSError as exc:
            logger.error("Could not save refinement history: %s", exc)

    @staticmethod
    def _latest_backup_dir(project_path: str) -> Optional[str]:
        """Return the most recently created timestamped backup directory, if any."""
        backup_root = os.path.join(project_path, _BACKUP_DIR)
        if not os.path.isdir(backup_root):
            return None
        subdirs = [
            entry.path
            for entry in os.scandir(backup_root)
            if entry.is_dir() and entry.name != "history.json"
        ]
        if not subdirs:
            return None
        return max(subdirs, key=os.path.getmtime)


# ---------------------------------------------------------------------------
# Module-level convenience instances
# ---------------------------------------------------------------------------

#: Singleton engine — import and use directly in routes / pipelines.
refinement_engine = RefinementEngine()

#: Singleton history tracker — also accessible via engine._history.
refinement_history = RefinementHistory()
