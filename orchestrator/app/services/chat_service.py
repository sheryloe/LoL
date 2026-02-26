from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Any

from app.utils.file_io import list_files, read_json, write_json, write_text
from app.utils.paths import project_subdir

SESSION_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{3,96}$")
SESSION_PREFIX = "chat_"


def _utc_now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


class ChatService:
    def _discussion_dir(self, project_id: str) -> Path:
        return project_subdir(project_id, "discussion")

    def _is_valid_session_id(self, session_id: str) -> bool:
        return bool(SESSION_ID_PATTERN.fullmatch(session_id.strip()))

    def _json_path(self, project_id: str, session_id: str) -> Path:
        return self._discussion_dir(project_id) / f"{session_id}.json"

    def _markdown_path(self, project_id: str, session_id: str) -> Path:
        return self._discussion_dir(project_id) / f"{session_id}.md"

    def _new_session_id(self) -> str:
        timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
        return f"{SESSION_PREFIX}{timestamp}"

    def new_session(self, project_id: str) -> dict[str, Any]:
        now = _utc_now_iso()
        return {
            "session_id": self._new_session_id(),
            "project_id": project_id,
            "created_at": now,
            "updated_at": now,
            "messages": [],
        }

    def get_session(self, project_id: str, session_id: str | None = None) -> dict[str, Any] | None:
        if session_id:
            safe_id = session_id.strip()
            if not self._is_valid_session_id(safe_id):
                return None
            payload = read_json(self._json_path(project_id, safe_id))
            return payload or None

        for path in self._session_files(project_id):
            payload = read_json(path)
            if payload:
                return payload
        return None

    def get_or_create_session(self, project_id: str, session_id: str | None = None) -> dict[str, Any]:
        existing = self.get_session(project_id=project_id, session_id=session_id)
        if existing:
            return existing
        return self.new_session(project_id)

    def append_message(
        self,
        session: dict[str, Any],
        role: str,
        content: str,
        worker: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        messages = session.setdefault("messages", [])
        now = _utc_now_iso()
        message: dict[str, Any] = {
            "id": f"msg_{len(messages) + 1:04d}",
            "role": role,
            "content": content.strip(),
            "created_at": now,
        }
        if worker:
            message["worker"] = worker
        if metadata:
            message["metadata"] = metadata
        messages.append(message)
        session["updated_at"] = now

    def save_session(self, project_id: str, session: dict[str, Any], write_enabled: bool) -> None:
        session_id = str(session.get("session_id", "")).strip()
        if not self._is_valid_session_id(session_id):
            raise ValueError(f"invalid session id: {session_id}")

        session["project_id"] = project_id
        session["updated_at"] = _utc_now_iso()

        json_path = self._json_path(project_id, session_id)
        md_path = self._markdown_path(project_id, session_id)
        write_json(json_path, session, write_enabled)
        write_text(md_path, self._to_markdown(session), write_enabled)

    def list_sessions(self, project_id: str) -> list[dict[str, Any]]:
        summaries: list[dict[str, Any]] = []
        for path in self._session_files(project_id):
            payload = read_json(path)
            if not payload:
                continue
            messages = payload.get("messages", [])
            summaries.append(
                {
                    "session_id": payload.get("session_id", path.stem),
                    "updated_at": payload.get("updated_at"),
                    "turn_count": len(messages),
                }
            )
        return summaries

    def _session_files(self, project_id: str) -> list[Path]:
        discussion = self._discussion_dir(project_id)
        files = list_files(discussion, f"{SESSION_PREFIX}*.json")
        files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return files

    def _to_markdown(self, session: dict[str, Any]) -> str:
        session_id = session.get("session_id", "-")
        created_at = session.get("created_at", "-")
        updated_at = session.get("updated_at", "-")
        lines = [
            "# Co-worker Discussion",
            "",
            f"- session_id: `{session_id}`",
            f"- created_at: `{created_at}`",
            f"- updated_at: `{updated_at}`",
            "",
            "## Messages",
            "",
        ]
        for idx, message in enumerate(session.get("messages", []), start=1):
            role = str(message.get("role", "unknown"))
            created = str(message.get("created_at", "-"))
            content = str(message.get("content", ""))
            lines.append(f"### {idx}. {role} ({created})")
            lines.append("")
            lines.append("```text")
            lines.append(content)
            lines.append("```")
            lines.append("")
        return "\n".join(lines).strip() + "\n"


chat_service = ChatService()
