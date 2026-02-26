from __future__ import annotations

from datetime import datetime
from typing import Any
from typing import Literal

from pydantic import BaseModel, Field

from app.config import WRITE_ENABLED_DEFAULT


class ProjectCreateRequest(BaseModel):
    project_id: str = Field(..., min_length=3, max_length=64)
    title: str | None = Field(default=None, max_length=120)
    write_enabled: bool = WRITE_ENABLED_DEFAULT


class ProjectSummary(BaseModel):
    project_id: str
    title: str | None = None
    created_at: datetime


class WorkerTaskInput(BaseModel):
    prompt: str = Field(..., min_length=1)
    model: str | None = None
    cli_args: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkerRunRequest(BaseModel):
    task: WorkerTaskInput
    write_enabled: bool = WRITE_ENABLED_DEFAULT


class WorkerResult(BaseModel):
    worker: str
    success: bool
    output_path: str
    metadata_path: str
    stdout: str
    stderr: str
    error: str | None = None
    started_at: datetime
    finished_at: datetime


class CoworkRunRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    session_id: str | None = None
    write_enabled: bool = WRITE_ENABLED_DEFAULT
    rounds: int = Field(default=1, ge=1, le=5)
    order: Literal["codex_then_gemini", "gemini_then_codex"] = "codex_then_gemini"
    codex_cli_args: list[str] = Field(default_factory=list)
    gemini_cli_args: list[str] = Field(default_factory=list)


class NotionPublishRequest(BaseModel):
    notion_token: str = Field(..., min_length=1)
    parent_page_id: str = Field(..., min_length=32, max_length=36)
    step_title: str = Field(..., min_length=1, max_length=120)
    one_line_summary: str = Field(..., min_length=1)
    background: str = Field(..., min_length=1)
    core_concepts: str = Field(..., min_length=1)
    implementation_details: str = Field(..., min_length=1)
    test_notes: str = Field(..., min_length=1)
    troubleshooting: str = Field(default="")
    next_steps: str = Field(..., min_length=1)
