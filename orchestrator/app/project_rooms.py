from __future__ import annotations

import asyncio
import json
import re
from datetime import UTC, datetime
from pathlib import Path

from .models import (
    DEFAULT_PIPELINE_STEPS,
    ProjectCreateRequest,
    ProjectSettings,
    ProjectSettingsPatchRequest,
    ProjectSettingsPutRequest,
    ProjectSummary,
)

PROJECT_SCHEMA_VERSION = 1
PROJECT_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{3,64}$")


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def validate_project_id(project_id: str) -> str:
    candidate = project_id.strip()
    if not PROJECT_ID_PATTERN.fullmatch(candidate):
        raise ValueError("project_id must be 3-64 chars and only contain letters, numbers, underscore, hyphen")
    return candidate


class ProjectRoomStore:
    def __init__(self, projects_dir: Path) -> None:
        self.projects_dir = projects_dir
        self.projects_dir.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()

    def _project_dir(self, project_id: str) -> Path:
        return self.projects_dir / project_id

    def _settings_path(self, project_id: str) -> Path:
        return self._project_dir(project_id) / "settings.json"

    def _default_settings(self, project_id: str, title: str | None = None) -> ProjectSettings:
        now = utc_now()
        return ProjectSettings(
            schema_version=PROJECT_SCHEMA_VERSION,
            project_id=project_id,
            title=title,
            default_session_id=project_id,
            default_cwd_relative=".",
            default_enable_fix=True,
            codex_cmd_template="",
            gemini_cmd_template="",
            pipeline_steps=list(DEFAULT_PIPELINE_STEPS),
            write_policy="read_only",
            created_at=now,
            updated_at=now,
        )

    def _read_settings(self, project_id: str) -> ProjectSettings:
        path = self._settings_path(project_id)
        if not path.exists():
            raise FileNotFoundError(f"project not found: {project_id}")

        raw = path.read_text(encoding="utf-8")
        loaded = json.loads(raw)
        defaults = self._default_settings(project_id).model_dump()
        merged = {**defaults, **loaded}
        merged["project_id"] = project_id
        if not merged.get("default_session_id"):
            merged["default_session_id"] = project_id
        merged["schema_version"] = PROJECT_SCHEMA_VERSION
        return ProjectSettings.model_validate(merged)

    def _write_settings(self, settings: ProjectSettings) -> None:
        project_id = validate_project_id(settings.project_id)
        path = self._settings_path(project_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = settings.model_dump()
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    async def list_projects(self) -> list[ProjectSummary]:
        items: list[ProjectSummary] = []
        for project_dir in sorted(self.projects_dir.iterdir(), key=lambda p: p.name.lower()):
            if not project_dir.is_dir():
                continue
            settings_path = project_dir / "settings.json"
            if not settings_path.exists():
                continue
            try:
                settings = self._read_settings(project_dir.name)
            except Exception:
                continue
            items.append(
                ProjectSummary(
                    project_id=settings.project_id,
                    title=settings.title,
                    created_at=settings.created_at,
                    updated_at=settings.updated_at,
                )
            )
        items.sort(key=lambda item: item.updated_at, reverse=True)
        return items

    async def ensure_project(self, project_id: str, title: str | None = None) -> ProjectSettings:
        safe_project_id = validate_project_id(project_id)
        async with self._lock:
            path = self._settings_path(safe_project_id)
            if path.exists():
                settings = self._read_settings(safe_project_id)
                if title is not None and title != settings.title:
                    updated = settings.model_copy(update={"title": title, "updated_at": utc_now()})
                    self._write_settings(updated)
                    return updated
                return settings

            settings = self._default_settings(safe_project_id, title=title)
            self._write_settings(settings)
            return settings

    async def create_project(self, req: ProjectCreateRequest) -> ProjectSettings:
        safe_project_id = validate_project_id(req.project_id)
        async with self._lock:
            path = self._settings_path(safe_project_id)
            if path.exists():
                raise ValueError(f"project already exists: {safe_project_id}")
            settings = self._default_settings(safe_project_id, title=req.title)
            self._write_settings(settings)
            return settings

    async def get_settings(self, project_id: str) -> ProjectSettings:
        safe_project_id = validate_project_id(project_id)
        return self._read_settings(safe_project_id)

    async def put_settings(self, project_id: str, req: ProjectSettingsPutRequest) -> ProjectSettings:
        safe_project_id = validate_project_id(project_id)
        current = await self.ensure_project(safe_project_id, title=req.title)
        async with self._lock:
            updated = ProjectSettings(
                schema_version=PROJECT_SCHEMA_VERSION,
                project_id=safe_project_id,
                title=req.title,
                default_session_id=req.default_session_id,
                default_cwd_relative=req.default_cwd_relative,
                default_enable_fix=req.default_enable_fix,
                codex_cmd_template=req.codex_cmd_template,
                gemini_cmd_template=req.gemini_cmd_template,
                pipeline_steps=req.pipeline_steps,
                write_policy=req.write_policy,
                created_at=current.created_at,
                updated_at=utc_now(),
            )
            self._write_settings(updated)
            return updated

    async def patch_settings(self, project_id: str, req: ProjectSettingsPatchRequest) -> ProjectSettings:
        safe_project_id = validate_project_id(project_id)
        current = await self.ensure_project(safe_project_id)
        async with self._lock:
            patch = req.model_dump(exclude_none=True)
            if not patch:
                return current
            patch["updated_at"] = utc_now()
            updated = current.model_copy(update=patch)
            self._write_settings(updated)
            return updated
