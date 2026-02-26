from __future__ import annotations

import re
from pathlib import Path

from app.config import PROJECTS_ROOT

PROJECT_SUBDIRS = [
    "spec",
    "tasks",
    "codex_outputs",
    "gemini_outputs",
    "artifacts",
    "discussion",
]

PROJECT_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{3,64}$")


def validate_project_id(project_id: str) -> str:
    cleaned = project_id.strip()
    if not PROJECT_ID_PATTERN.fullmatch(cleaned):
        raise ValueError(
            "project_id must be 3-64 chars and only contain letters, numbers, underscore, hyphen"
        )
    return cleaned


def project_root(project_id: str) -> Path:
    return PROJECTS_ROOT / validate_project_id(project_id)


def project_subdir(project_id: str, subdir: str) -> Path:
    if subdir not in PROJECT_SUBDIRS:
        raise ValueError(f"invalid project subdir: {subdir}")
    return project_root(project_id) / subdir
