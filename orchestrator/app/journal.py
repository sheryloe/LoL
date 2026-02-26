from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


class JournalStore:
    def __init__(self, journal_dir: Path) -> None:
        self.journal_dir = journal_dir
        self.journal_dir.mkdir(parents=True, exist_ok=True)
        self._locks: dict[str, asyncio.Lock] = {}

    def _lock_for(self, session_id: str) -> asyncio.Lock:
        lock = self._locks.get(session_id)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[session_id] = lock
        return lock

    def path_for(self, session_id: str) -> Path:
        safe = session_id.replace("/", "_").replace("\\", "_")
        return self.journal_dir / f"{safe}.ndjson"

    async def append(self, session_id: str, payload: dict[str, Any]) -> None:
        event = {"timestamp": utc_now(), **payload}
        path = self.path_for(session_id)
        lock = self._lock_for(session_id)
        async with lock:
            with path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(event, ensure_ascii=False) + "\n")

    async def read(self, session_id: str, limit: int = 200) -> list[dict[str, Any]]:
        path = self.path_for(session_id)
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

