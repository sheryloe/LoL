from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

PipelineStep = Literal["plan", "implement", "review", "fix"]
DEFAULT_PIPELINE_STEPS: list[PipelineStep] = ["plan", "implement", "review", "fix"]


class ChatRequest(BaseModel):
    project_id: str | None = None
    session_id: str | None = None
    message: str = Field(min_length=1)
    cwd_relative: str | None = None
    enable_fix: bool | None = None


class ResolvedChatRequest(BaseModel):
    project_id: str = Field(min_length=3, max_length=64)
    session_id: str = Field(min_length=1)
    message: str = Field(min_length=1)
    cwd_relative: str = "."
    enable_fix: bool = True
    codex_cmd_template: str = ""
    gemini_cmd_template: str = ""
    pipeline_steps: list[PipelineStep] = Field(default_factory=lambda: list(DEFAULT_PIPELINE_STEPS))

    @field_validator("pipeline_steps")
    @classmethod
    def validate_pipeline_steps(cls, value: list[PipelineStep]) -> list[PipelineStep]:
        if not value:
            raise ValueError("pipeline_steps must contain at least one step")
        if len(value) != len(set(value)):
            raise ValueError("pipeline_steps must not contain duplicates")
        return value


class ChatResponse(BaseModel):
    project_id: str
    workflow_job_id: str
    session_id: str
    status: str


class ProjectCreateRequest(BaseModel):
    project_id: str = Field(min_length=3, max_length=64)
    title: str | None = Field(default=None, max_length=120)


class ProjectSummary(BaseModel):
    project_id: str
    title: str | None = None
    created_at: str
    updated_at: str


class ProjectSettings(BaseModel):
    schema_version: int = 1
    project_id: str = Field(min_length=3, max_length=64)
    title: str | None = Field(default=None, max_length=120)
    default_session_id: str = Field(min_length=1)
    default_cwd_relative: str = "."
    default_enable_fix: bool = True
    codex_cmd_template: str = ""
    gemini_cmd_template: str = ""
    pipeline_steps: list[PipelineStep] = Field(default_factory=lambda: list(DEFAULT_PIPELINE_STEPS))
    write_policy: Literal["read_only", "write_enabled"] = "read_only"
    created_at: str
    updated_at: str

    @field_validator("pipeline_steps")
    @classmethod
    def validate_pipeline_steps(cls, value: list[PipelineStep]) -> list[PipelineStep]:
        if not value:
            raise ValueError("pipeline_steps must contain at least one step")
        if len(value) != len(set(value)):
            raise ValueError("pipeline_steps must not contain duplicates")
        return value


class ProjectSettingsPutRequest(BaseModel):
    title: str | None = Field(default=None, max_length=120)
    default_session_id: str = Field(min_length=1)
    default_cwd_relative: str = "."
    default_enable_fix: bool = True
    codex_cmd_template: str = ""
    gemini_cmd_template: str = ""
    pipeline_steps: list[PipelineStep] = Field(default_factory=lambda: list(DEFAULT_PIPELINE_STEPS))
    write_policy: Literal["read_only", "write_enabled"] = "read_only"

    @field_validator("pipeline_steps")
    @classmethod
    def validate_pipeline_steps(cls, value: list[PipelineStep]) -> list[PipelineStep]:
        if not value:
            raise ValueError("pipeline_steps must contain at least one step")
        if len(value) != len(set(value)):
            raise ValueError("pipeline_steps must not contain duplicates")
        return value


class ProjectSettingsPatchRequest(BaseModel):
    title: str | None = Field(default=None, max_length=120)
    default_session_id: str | None = None
    default_cwd_relative: str | None = None
    default_enable_fix: bool | None = None
    codex_cmd_template: str | None = None
    gemini_cmd_template: str | None = None
    pipeline_steps: list[PipelineStep] | None = None
    write_policy: Literal["read_only", "write_enabled"] | None = None

    @field_validator("pipeline_steps")
    @classmethod
    def validate_pipeline_steps(cls, value: list[PipelineStep] | None) -> list[PipelineStep] | None:
        if value is None:
            return value
        if not value:
            raise ValueError("pipeline_steps must contain at least one step")
        if len(value) != len(set(value)):
            raise ValueError("pipeline_steps must not contain duplicates")
        return value
