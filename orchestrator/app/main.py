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
from .journal import JournalStore
from .models import ChatRequest, ChatResponse
from .runner_client import RunnerClient
from .security import PathSecurityError, resolve_under_root
from .workflow import WorkflowManager

config = load_config()
journal = JournalStore(config.journal_dir)
runner_client = RunnerClient(config.runner_base_url)
workflow_manager = WorkflowManager(runner_client, journal)
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
    }


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(static_dir / "index.html")


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


@app.post("/api/chat", response_model=ChatResponse)
async def start_chat(req: ChatRequest) -> ChatResponse:
    job = await workflow_manager.start(req)
    return ChatResponse(workflow_job_id=job.workflow_job_id, session_id=job.session_id, status=job.status)


@app.get("/api/workflow/{workflow_job_id}")
async def get_workflow(workflow_job_id: str) -> dict:
    job = workflow_manager.get(workflow_job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="workflow not found")
    return {
        "workflow_job_id": job.workflow_job_id,
        "session_id": job.session_id,
        "status": job.status,
        "cwd_relative": job.cwd_relative,
        "started_at": job.started_at,
        "ended_at": job.ended_at,
        "artifacts": job.artifacts,
    }


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
