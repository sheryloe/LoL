from __future__ import annotations

import json
from collections.abc import AsyncIterator
from pathlib import Path

from fastapi import FastAPI
from fastapi import HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

from .config import load_config
from .conversations import ProjectConversationStore
from .journal import JournalStore
from .models import (
    ChatRequest,
    ChatResponse,
    ProjectCreateRequest,
    ProjectSettings,
    ProjectSettingsPatchRequest,
    ProjectSettingsPutRequest,
)
from .models import ResolvedChatRequest
from .project_rooms import ProjectRoomStore
from .runner_client import RunnerClient
from .run_store import WorkflowRunStore
from .security import PathSecurityError, resolve_under_root
from .workflow import WorkflowManager

config = load_config()
journal = JournalStore(config.journal_dir)
project_store = ProjectRoomStore(config.projects_dir)
conversation_store = ProjectConversationStore(config.projects_dir)
run_store = WorkflowRunStore(config.projects_dir)
runner_client = RunnerClient(config.runner_base_url)
workflow_manager = WorkflowManager(runner_client, journal, conversation_store, run_store)
app = FastAPI(title="LoL Orchestrator", version="0.1.0")
static_dir = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "ok",
        "runner_base_url": config.runner_base_url,
        "root_dir": str(config.root_dir),
        "journal_dir": str(config.journal_dir),
        "projects_dir": str(config.projects_dir),
    }


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(static_dir / "index.html")


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


@app.post("/api/chat", response_model=ChatResponse)
async def start_chat(req: ChatRequest) -> ChatResponse:
    project_id = (req.project_id or req.session_id or "default_room").strip()
    try:
        settings = await project_store.ensure_project(project_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    resolved = ResolvedChatRequest(
        project_id=settings.project_id,
        session_id=(req.session_id or settings.default_session_id).strip(),
        message=req.message,
        cwd_relative=(req.cwd_relative or settings.default_cwd_relative).strip() or ".",
        enable_fix=settings.default_enable_fix if req.enable_fix is None else req.enable_fix,
        codex_cmd_template=settings.codex_cmd_template,
        gemini_cmd_template=settings.gemini_cmd_template,
        pipeline_steps=settings.pipeline_steps,
    )
    await conversation_store.append(
        resolved.project_id,
        {
            "source": "user_message",
            "project_id": resolved.project_id,
            "session_id": resolved.session_id,
            "message": resolved.message,
        },
    )
    job = await workflow_manager.start(resolved)
    await conversation_store.append(
        resolved.project_id,
        {
            "source": "system",
            "project_id": resolved.project_id,
            "session_id": resolved.session_id,
            "workflow_job_id": job.workflow_job_id,
            "event": "workflow_queued",
        },
    )
    return ChatResponse(
        project_id=job.project_id,
        workflow_job_id=job.workflow_job_id,
        session_id=job.session_id,
        status=job.status,
    )


@app.get("/api/workflow/{workflow_job_id}")
async def get_workflow(workflow_job_id: str) -> dict:
    job = workflow_manager.get(workflow_job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="workflow not found")
    return {
        "workflow_job_id": job.workflow_job_id,
        "project_id": job.project_id,
        "session_id": job.session_id,
        "status": job.status,
        "cwd_relative": job.cwd_relative,
        "started_at": job.started_at,
        "ended_at": job.ended_at,
        "artifacts": job.artifacts,
    }


@app.post("/api/workflow/{workflow_job_id}/cancel")
async def cancel_workflow(workflow_job_id: str) -> dict:
    job = workflow_manager.get(workflow_job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="workflow not found")
    if job.status in {"completed", "failed", "canceled"}:
        raise HTTPException(status_code=409, detail=f"workflow already {job.status}")
    canceled = await workflow_manager.cancel(workflow_job_id)
    if not canceled:
        raise HTTPException(status_code=409, detail="workflow cancel rejected")
    return {"workflow_job_id": workflow_job_id, "status": "canceled"}


@app.get("/api/workflow/stream/{workflow_job_id}")
async def stream_workflow(workflow_job_id: str, cursor: int = Query(default=0, ge=0)) -> StreamingResponse:
    job = workflow_manager.get(workflow_job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="workflow not found")

    async def event_stream() -> AsyncIterator[str]:
        async for event in workflow_manager.stream(workflow_job_id, cursor=cursor):
            yield _sse(event)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/api/session/{session_id}/journal")
async def get_journal(session_id: str, limit: int = Query(default=200, ge=1, le=1000)) -> dict:
    items = await journal.read(session_id=session_id, limit=limit)
    return {"session_id": session_id, "items": items}


@app.get("/api/projects")
async def list_projects() -> dict:
    return {"items": await project_store.list_projects()}


@app.post("/api/projects", response_model=ProjectSettings)
async def create_project(req: ProjectCreateRequest) -> ProjectSettings:
    try:
        return await project_store.create_project(req)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/projects/{project_id}/settings", response_model=ProjectSettings)
async def get_project_settings(project_id: str) -> ProjectSettings:
    try:
        return await project_store.get_settings(project_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.put("/api/projects/{project_id}/settings", response_model=ProjectSettings)
async def put_project_settings(project_id: str, req: ProjectSettingsPutRequest) -> ProjectSettings:
    try:
        return await project_store.put_settings(project_id, req)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.patch("/api/projects/{project_id}/settings", response_model=ProjectSettings)
async def patch_project_settings(project_id: str, req: ProjectSettingsPatchRequest) -> ProjectSettings:
    try:
        return await project_store.patch_settings(project_id, req)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/projects/{project_id}/conversation")
async def get_project_conversation(project_id: str, limit: int = Query(default=200, ge=1, le=2000)) -> dict:
    try:
        settings = await project_store.get_settings(project_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    items = await conversation_store.read(settings.project_id, limit=limit)
    return {"project_id": settings.project_id, "items": items}


@app.get("/api/projects/{project_id}/runs")
async def list_project_runs(project_id: str, limit: int = Query(default=100, ge=1, le=500)) -> dict:
    try:
        settings = await project_store.get_settings(project_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    items = await run_store.list(settings.project_id, limit=limit)
    return {"project_id": settings.project_id, "items": items}


@app.get("/api/projects/{project_id}/runs/{workflow_job_id}")
async def get_project_run(project_id: str, workflow_job_id: str) -> dict:
    try:
        settings = await project_store.get_settings(project_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    try:
        return await run_store.get(settings.project_id, workflow_job_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/files")
async def list_files(path: str = ".") -> dict:
    try:
        target = resolve_under_root(config.root_dir, path)
    except PathSecurityError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not target.exists():
        raise HTTPException(status_code=404, detail="path not found")
    if not target.is_dir():
        raise HTTPException(status_code=400, detail="path must be a directory")

    entries: list[dict] = []
    for item in sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))[:500]:
        stat = item.stat()
        entries.append(
            {
                "name": item.name,
                "path": str(item.relative_to(config.root_dir)).replace("\\", "/"),
                "type": "dir" if item.is_dir() else "file",
                "size": stat.st_size,
                "modified": stat.st_mtime,
            }
        )
    rel = str(target.relative_to(config.root_dir)).replace("\\", "/")
    return {"root": ".", "path": rel if rel else ".", "entries": entries}


@app.get("/api/file")
async def read_file(path: str) -> dict:
    try:
        target = resolve_under_root(config.root_dir, path)
    except PathSecurityError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="file not found")
    if target.stat().st_size > 512_000:
        raise HTTPException(status_code=413, detail="file too large (>500KB)")
    content = target.read_text(encoding="utf-8", errors="replace")
    rel = str(target.relative_to(config.root_dir)).replace("\\", "/")
    return {"path": rel, "content": content}
