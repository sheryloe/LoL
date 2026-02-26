from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

PipelineStep = Literal["plan", "implement", "review", "fix"]
DEFAULT_PIPELINE_STEPS: list[PipelineStep] = ["plan", "implement", "review", "fix"]


class ChatRequest(BaseModel):
    project_id: str | None = None
    session_id: str | None = None
    message: str = Field(min_length=1)
    cwd_relative: str | None = None
    enable_fix: bool | None = None
    include_rag: bool = True
    rag_top_k: int = Field(default=4, ge=1, le=20)
    rag_max_chars: int = Field(default=2200, ge=200, le=12000)


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


class RunnerAuthRuntimeKeysRequest(BaseModel):
    openai_api_key: str | None = None
    gemini_api_key: str | None = None
    persist: bool = True


class RunnerCodexDeviceAuthStartRequest(BaseModel):
    session_id: str = Field(default="runner-auth-codex", min_length=1)


class RagIngestRequest(BaseModel):
    source_type: Literal["text", "file"] = "text"
    title: str | None = Field(default=None, max_length=180)
    content: str | None = None
    source_path: str | None = None
    tags: list[str] = Field(default_factory=list)

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, value: list[str]) -> list[str]:
        normalized: list[str] = []
        for item in value:
            clean = item.strip().lower()
            if clean and clean not in normalized:
                normalized.append(clean)
        return normalized[:12]

    @model_validator(mode="after")
    def validate_source_payload(self) -> "RagIngestRequest":
        if self.source_type == "text":
            if not self.content or not self.content.strip():
                raise ValueError("content is required when source_type=text")
            return self
        if self.source_type == "file":
            if not self.source_path or not self.source_path.strip():
                raise ValueError("source_path is required when source_type=file")
            return self
        raise ValueError("unsupported source_type")


class RagSearchRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)
    max_chars: int = Field(default=2400, ge=200, le=12000)
