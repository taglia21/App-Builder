"""
Multi-turn Refinement Chat for Ignara.

Manages conversation history for iterative project customization.
Users can have ongoing conversations about changes to their generated
projects, with full context of what was previously discussed and changed.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from src.code_generation.refinement import (
    RefinementEngine,
    RefinementRequest,
    RefinementResult,
)

logger = logging.getLogger(__name__)


class ChatMessage(BaseModel):
    """A single message in a refinement conversation."""
    role: str = Field(..., description="'user' or 'assistant'")
    content: str = Field(..., description="Message content")
    timestamp: str = Field(default_factory=lambda: datetime.now(tz=timezone.utc).isoformat())
    refinement_result: Optional[Dict[str, Any]] = Field(default=None, description="Attached refinement result if this was an applied change")


class RefinementChat(BaseModel):
    """A multi-turn conversation about refining a generated project."""
    chat_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    project_path: str
    project_id: Optional[str] = None
    messages: List[ChatMessage] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now(tz=timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(tz=timezone.utc).isoformat())

    def add_user_message(self, content: str) -> ChatMessage:
        msg = ChatMessage(role="user", content=content)
        self.messages.append(msg)
        self.updated_at = datetime.now(tz=timezone.utc).isoformat()
        return msg

    def add_assistant_message(self, content: str, refinement_result: Optional[Dict[str, Any]] = None) -> ChatMessage:
        msg = ChatMessage(role="assistant", content=content, refinement_result=refinement_result)
        self.messages.append(msg)
        self.updated_at = datetime.now(tz=timezone.utc).isoformat()
        return msg

    def get_context_summary(self, max_messages: int = 10) -> str:
        """Build a summary of recent conversation for LLM context."""
        recent = self.messages[-max_messages:]
        lines = []
        for msg in recent:
            prefix = "User" if msg.role == "user" else "Assistant"
            lines.append(f"{prefix}: {msg.content}")
            if msg.refinement_result:
                modified = msg.refinement_result.get("files_modified", [])
                created = msg.refinement_result.get("files_created", [])
                if modified or created:
                    file_list = [f.get("path", "") for f in modified + created]
                    lines.append(f"  [Changed files: {', '.join(file_list[:5])}]")
        return "\n".join(lines)


class ChatManager:
    """Manages active refinement chat sessions."""

    def __init__(self):
        self._chats: Dict[str, RefinementChat] = {}
        self._engine = RefinementEngine()

    def create_chat(self, project_path: str, project_id: Optional[str] = None) -> RefinementChat:
        chat = RefinementChat(project_path=project_path, project_id=project_id)
        self._chats[chat.chat_id] = chat
        logger.info("Created refinement chat %s for project %s", chat.chat_id, project_path)
        return chat

    def get_chat(self, chat_id: str) -> Optional[RefinementChat]:
        return self._chats.get(chat_id)

    def list_chats(self, project_path: Optional[str] = None) -> List[RefinementChat]:
        chats = list(self._chats.values())
        if project_path:
            chats = [c for c in chats if c.project_path == project_path]
        return sorted(chats, key=lambda c: c.updated_at, reverse=True)

    def delete_chat(self, chat_id: str) -> bool:
        if chat_id in self._chats:
            del self._chats[chat_id]
            return True
        return False

    async def send_message(
        self,
        chat_id: str,
        instruction: str,
        scope: Optional[str] = None,
        apply_changes: bool = True,
    ) -> Dict[str, Any]:
        """Process a user message in a chat, optionally applying changes.

        Args:
            chat_id: The chat session ID
            instruction: The user's natural-language instruction
            scope: Optional scope restriction
            apply_changes: If True, actually apply the refinement. If False, just plan.

        Returns:
            Dict with keys: message, refinement_result (if applied), plan (if not applied)
        """
        chat = self._chats.get(chat_id)
        if not chat:
            raise ValueError(f"Chat {chat_id} not found")

        # Add user message
        chat.add_user_message(instruction)

        # Build enriched instruction with conversation context
        context_summary = chat.get_context_summary()
        enriched_instruction = instruction
        if len(chat.messages) > 1:
            enriched_instruction = (
                f"Previous conversation context:\n{context_summary}\n\n"
                f"Current instruction: {instruction}"
            )

        if apply_changes:
            # Apply the refinement
            try:
                result = await self._engine.refine(
                    RefinementRequest(
                        instruction=enriched_instruction,
                        project_path=chat.project_path,
                        scope=scope,
                    )
                )
                result_dict = {
                    "files_modified": [fc.model_dump() for fc in result.files_modified],
                    "files_created": [fc.model_dump() for fc in result.files_created],
                    "files_deleted": [fc.model_dump() for fc in result.files_deleted],
                    "explanation": result.explanation,
                    "warnings": result.warnings,
                }

                # Add assistant response
                chat.add_assistant_message(
                    content=result.explanation,
                    refinement_result=result_dict,
                )

                return {"message": result.explanation, "refinement_result": result_dict}
            except Exception as exc:
                error_msg = f"Refinement failed: {exc}"
                chat.add_assistant_message(content=error_msg)
                return {"message": error_msg, "error": str(exc)}
        else:
            # Just acknowledge — in future could do a "dry run" planning step
            chat.add_assistant_message(content=f"Noted: {instruction}. Send another message or ask me to apply changes.")
            return {"message": f"Noted: {instruction}"}


# Module-level singleton
chat_manager = ChatManager()
