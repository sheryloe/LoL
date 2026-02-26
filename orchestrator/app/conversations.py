from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


class ProjectConversationStore:
    def __init__(self, projects_dir: Path) -> None:
        self.projects_dir = projects_dir
        self.projects_dir.mkdir(parents=True, exist_ok=True)
        self._locks: dict[str, asyncio.Lock] = {}

    def _lock_for(self, project_id: str) -> asyncio.Lock:
        lock = self._locks.get(project_id)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[project_id] = lock
        return lock

    def path_for(self, project_id: str) -> Path:
        safe = project_id.replace("/", "_").replace("\\", "_")
        return self.projects_dir / safe / "conversation.ndjson"

    async def append(self, project_id: str, payload: dict[str, Any]) -> None:
        event = {"timestamp": utc_now(), **payload}
        path = self.path_for(project_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        lock = self._lock_for(project_id)
        async with lock:
            with path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(event, ensure_ascii=False) + "\n")

    async def read(self, project_id: str, limit: int = 200) -> list[dict[str, Any]]:
        path = self.path_for(project_id)
        if not path.exists():
            return []
        lines = path.read_text(encoding="utf-8").splitlines()
        sliced = lines[-limit:]
        result: list[dict[str, Any]] = []
        for line in sliced:
            try:
                result.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return result
