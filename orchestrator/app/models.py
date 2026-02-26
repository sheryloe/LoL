from __future__ import annotations

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1)
    message: str = Field(min_length=1)
    cwd_relative: str = "."
    enable_fix: bool = True


class ChatResponse(BaseModel):
    workflow_job_id: str
    session_id: str
    status: str

