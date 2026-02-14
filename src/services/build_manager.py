"""
Build Manager Service

Manages build lifecycle, persistence via SQLite, and in-memory event streaming.
"""

import logging
import sqlite3
import threading
import uuid
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Database file location
_DB_PATH = Path("valeric_builds.db")


class BuildManager:
    """Manages pipeline build state, persistence, and SSE event buffers."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self._db_path = db_path or _DB_PATH
        self._events: dict[str, deque[dict[str, Any]]] = {}
        self._lock = threading.Lock()
        self._init_db()

    # ------------------------------------------------------------------ DB
    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path), timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_db(self) -> None:
        with self._get_conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS builds (
                    build_id       TEXT PRIMARY KEY,
                    idea           TEXT NOT NULL,
                    status         TEXT NOT NULL DEFAULT 'pending',
                    current_stage  TEXT NOT NULL DEFAULT '',
                    progress       INTEGER NOT NULL DEFAULT 0,
                    llm_provider   TEXT NOT NULL DEFAULT 'auto',
                    theme          TEXT NOT NULL DEFAULT 'Modern',
                    started_at     TEXT NOT NULL,
                    completed_at   TEXT,
                    output_path    TEXT,
                    error_message  TEXT
                )
                """
            )

    # ------------------------------------------------------------------ CRUD
    def create_build(
        self,
        idea: str,
        llm_provider: str = "auto",
        theme: str = "Modern",
    ) -> str:
        """Create a new build record and return its id."""
        build_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        with self._get_conn() as conn:
            conn.execute(
                """
                INSERT INTO builds
                    (build_id, idea, status, current_stage, progress,
                     llm_provider, theme, started_at)
                VALUES (?, ?, 'pending', '', 0, ?, ?, ?)
                """,
                (build_id, idea, llm_provider, theme, now),
            )
        # Initialise event buffer
        with self._lock:
            self._events[build_id] = deque(maxlen=500)
        logger.info("Created build %s", build_id)
        return build_id

    def get_build(self, build_id: str) -> Optional[dict[str, Any]]:
        """Return a single build as dict, or None."""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM builds WHERE build_id = ?", (build_id,)
            ).fetchone()
        return dict(row) if row else None

    def list_builds(self, limit: int = 50) -> list[dict[str, Any]]:
        """Return most-recent builds, newest first."""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM builds ORDER BY started_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    def update_build(self, build_id: str, **kwargs: Any) -> None:
        """Update arbitrary columns on a build row."""
        if not kwargs:
            return
        cols = ", ".join(f"{k} = ?" for k in kwargs)
        vals = list(kwargs.values())
        vals.append(build_id)
        with self._get_conn() as conn:
            conn.execute(
                f"UPDATE builds SET {cols} WHERE build_id = ?",  # noqa: S608
                vals,
            )

    # ------------------------------------------------------------------ Events
    def push_event(self, build_id: str, event: dict[str, Any]) -> None:
        """Append an SSE event dict to the in-memory buffer (thread-safe)."""
        with self._lock:
            buf = self._events.setdefault(build_id, deque(maxlen=500))
            buf.append(event)

    def get_events(self, build_id: str) -> list[dict[str, Any]]:
        """Return and drain the event buffer for *build_id*."""
        with self._lock:
            buf = self._events.get(build_id)
            if not buf:
                return []
            events = list(buf)
            buf.clear()
            return events


# Module-level singleton
build_manager = BuildManager()
