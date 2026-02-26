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
    RagIngestRequest,
    RagSearchRequest,
    RunnerAuthRuntimeKeysRequest,
    RunnerCodexDeviceAuthStartRequest,
)
from .models import ResolvedChatRequest
from .project_rooms import ProjectRoomStore
from .rag_store import ProjectRagStore
from .runner_client import RunnerClient
from .run_store import WorkflowRunStore
from .security import PathSecurityError, resolve_under_root
from .workflow import WorkflowManager

config = load_config()
journal = JournalStore(config.journal_dir)
project_store = ProjectRoomStore(config.projects_dir)
conversation_store = ProjectConversationStore(config.projects_dir)
run_store = WorkflowRunStore(config.projects_dir)
rag_store = ProjectRagStore(config.projects_dir, config.root_dir)
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


@app.get("/api/runner/preflight")
async def runner_preflight(cwd_relative: str = ".") -> dict:
    try:
        return await runner_client.preflight_report(cwd_relative, timeout_sec=8.0)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/api/runner/auth/urls")
async def runner_auth_urls() -> dict:
    try:
        return await runner_client.get_auth_urls(timeout_sec=8.0)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/api/runner/auth/runtime")
async def runner_auth_runtime() -> dict:
    try:
        return await runner_client.get_auth_runtime(timeout_sec=8.0)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/api/runner/auth/runtime-keys")
async def runner_set_auth_runtime_keys(req: RunnerAuthRuntimeKeysRequest) -> dict:
    try:
        return await runner_client.set_auth_runtime_keys(
            openai_api_key=req.openai_api_key,
            gemini_api_key=req.gemini_api_key,
            persist=req.persist,
            timeout_sec=12.0,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/api/runner/auth/codex/device/start")
async def runner_start_codex_device_auth(req: RunnerCodexDeviceAuthStartRequest) -> dict:
    try:
        return await runner_client.start_codex_device_auth(req.session_id, timeout_sec=8.0)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/api/runner/jobs/{job_id}")
async def runner_job_status(job_id: str) -> dict:
    try:
        return await runner_client.get_job(job_id)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/api/runner/jobs/{job_id}/cancel")
async def runner_cancel_job(job_id: str) -> dict:
    try:
        return await runner_client.cancel_job(job_id)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


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

    session_id = (req.session_id or settings.default_session_id).strip()
    cwd_relative = (req.cwd_relative or settings.default_cwd_relative).strip() or "."
    enable_fix = settings.default_enable_fix if req.enable_fix is None else req.enable_fix
    try:
        await runner_client.preflight(cwd_relative, timeout_sec=8.0)
    except RuntimeError as exc:
        raise HTTPException(status_code=412, detail=str(exc)) from exc

    message_for_agent = req.message
    rag_hits: list[dict] = []
    if req.include_rag:
        rag_payload = await rag_store.build_context(
            settings.project_id,
            req.message,
            top_k=req.rag_top_k,
            max_chars=req.rag_max_chars,
        )
        rag_context = rag_payload.get("context", "")
        rag_hits = rag_payload.get("hits", [])
        if rag_context:
            message_for_agent = (
                "Use the following retrieved project context only when it is relevant. "
                "If context conflicts with the latest instruction, call out uncertainty and continue safely.\n\n"
                "### Retrieved Project Context\n"
                f"{rag_context}\n\n"
                "### User Request\n"
                f"{req.message}"
            )

    resolved = ResolvedChatRequest(
        project_id=settings.project_id,
        session_id=session_id,
        message=message_for_agent,
        cwd_relative=cwd_relative,
        enable_fix=enable_fix,
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
            "message": req.message,
            "rag_enabled": req.include_rag,
            "rag_hit_count": len(rag_hits),
        },
    )
    if rag_hits:
        await conversation_store.append(
            resolved.project_id,
            {
                "source": "rag",
                "project_id": resolved.project_id,
                "session_id": resolved.session_id,
                "event": "context_attached",
                "query": req.message,
                "top_k": req.rag_top_k,
                "hit_count": len(rag_hits),
                "hits": [
                    {
                        "document_id": hit.get("document_id"),
                        "chunk_id": hit.get("chunk_id"),
                        "title": hit.get("title"),
                        "score": hit.get("score"),
                        "source_path": hit.get("source_path"),
                    }
                    for hit in rag_hits
                ],
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


@app.get("/api/runner/jobs/stream/{job_id}")
async def stream_runner_job(job_id: str) -> StreamingResponse:
    async def event_stream() -> AsyncIterator[str]:
        async for event in runner_client.stream_job(job_id):
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


@app.get("/api/projects/{project_id}/rag/documents")
async def list_project_rag_documents(project_id: str) -> dict:
    try:
        settings = await project_store.get_settings(project_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    items = await rag_store.list_documents(settings.project_id)
    return {"project_id": settings.project_id, "items": items}


@app.post("/api/projects/{project_id}/rag/documents")
async def ingest_project_rag_document(project_id: str, req: RagIngestRequest) -> dict:
    try:
        settings = await project_store.get_settings(project_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    try:
        if req.source_type == "file":
            item = await rag_store.ingest_file(
                settings.project_id,
                source_path=req.source_path or "",
                title=req.title,
                tags=req.tags,
            )
        else:
            item = await rag_store.ingest_text(
                settings.project_id,
                title=req.title,
                content=req.content or "",
                tags=req.tags,
            )
    except PathSecurityError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    await conversation_store.append(
        settings.project_id,
        {
            "source": "rag",
            "project_id": settings.project_id,
            "session_id": settings.default_session_id,
            "event": "document_ingested",
            "document_id": item.get("document_id"),
            "title": item.get("title"),
            "source_type": item.get("source_type"),
            "source_path": item.get("source_path"),
            "chunk_count": item.get("chunk_count"),
        },
    )
    return {"project_id": settings.project_id, "item": item}


@app.post("/api/projects/{project_id}/rag/search")
async def search_project_rag(project_id: str, req: RagSearchRequest) -> dict:
    try:
        settings = await project_store.get_settings(project_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    payload = await rag_store.build_context(
        settings.project_id,
        req.query,
        top_k=req.top_k,
        max_chars=req.max_chars,
    )
    return {
        "project_id": settings.project_id,
        "query": req.query,
        "top_k": req.top_k,
        "hits": payload.get("hits", []),
        "context": payload.get("context", ""),
    }


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
