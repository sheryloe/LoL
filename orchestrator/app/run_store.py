from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any


class WorkflowRunStore:
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

    def _runs_dir(self, project_id: str) -> Path:
        return self.projects_dir / project_id / "runs"

    def _run_path(self, project_id: str, workflow_job_id: str) -> Path:
        return self._runs_dir(project_id) / f"{workflow_job_id}.json"

    async def upsert(self, project_id: str, workflow_job_id: str, payload: dict[str, Any]) -> None:
        path = self._run_path(project_id, workflow_job_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        lock = self._lock_for(project_id)
        async with lock:
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    async def get(self, project_id: str, workflow_job_id: str) -> dict[str, Any]:
        path = self._run_path(project_id, workflow_job_id)
        if not path.exists():
            raise FileNotFoundError(f"run not found: {workflow_job_id}")
        return json.loads(path.read_text(encoding="utf-8"))

    async def list(self, project_id: str, limit: int = 100) -> list[dict[str, Any]]:
        runs_dir = self._runs_dir(project_id)
        if not runs_dir.exists():
            return []

        items: list[dict[str, Any]] = []
        for run_file in sorted(runs_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]:
            try:
                payload = json.loads(run_file.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            summary = {
                "workflow_job_id": payload.get("workflow_job_id"),
                "project_id": payload.get("project_id"),
                "session_id": payload.get("session_id"),
                "status": payload.get("status"),
                "started_at": payload.get("started_at"),
                "ended_at": payload.get("ended_at"),
                "updated_at": payload.get("updated_at"),
            }
            items.append(summary)
        return items
