from __future__ import annotations

from pydantic import BaseModel, Field


class RunRequest(BaseModel):
    session_id: str = Field(min_length=1)
    prompt: str = Field(min_length=1)
    cwd_relative: str = "."
    command_template: str | None = None


class RunResponse(BaseModel):
    job_id: str
    status: str


class CommitRequest(BaseModel):
    cwd_relative: str = "."
    message: str = Field(min_length=1)
    add_all: bool = True


class PushRequest(BaseModel):
    cwd_relative: str = "."
    remote: str = "origin"
    branch: str | None = None


class AuthRuntimeKeysRequest(BaseModel):
    openai_api_key: str | None = None
    gemini_api_key: str | None = None
    persist: bool = True


class AuthCodexDeviceStartRequest(BaseModel):
    session_id: str = "runner-auth-codex"
