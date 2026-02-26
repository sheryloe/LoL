from __future__ import annotations

import json
from collections.abc import AsyncIterator

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse

from .config import load_config
from .git_ops import run_git
from .job_manager import JobManager, build_command
from .models import CommitRequest, PushRequest, RunRequest, RunResponse
from .security import PathSecurityError, resolve_cwd

app = FastAPI(title="LoL Host Runner", version="0.1.0")
config = load_config()
jobs = JobManager()


@app.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "ok",
        "root_dir": str(config.root_dir),
        "write_enabled": str(config.write_enabled),
    }


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


@app.post("/run/codex", response_model=RunResponse)
async def run_codex(req: RunRequest) -> RunResponse:
    try:
        cwd = resolve_cwd(config.root_dir, req.cwd_relative)
    except PathSecurityError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    command = build_command(config.codex_cmd, req.prompt)
    job = await jobs.create(req.session_id, "codex", cwd, command, req.prompt)
    return RunResponse(job_id=job.job_id, status=job.status)


@app.post("/run/gemini", response_model=RunResponse)
async def run_gemini(req: RunRequest) -> RunResponse:
    try:
        cwd = resolve_cwd(config.root_dir, req.cwd_relative)
    except PathSecurityError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    command = build_command(config.gemini_cmd, req.prompt)
    job = await jobs.create(req.session_id, "gemini", cwd, command, req.prompt)
    return RunResponse(job_id=job.job_id, status=job.status)


@app.get("/jobs/{job_id}")
async def get_job(job_id: str) -> dict:
    job = jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return {
        "job_id": job.job_id,
        "session_id": job.session_id,
        "runner": job.runner,
        "status": job.status,
        "return_code": job.return_code,
        "cwd": str(job.cwd),
        "command": job.command,
        "started_at": job.started_at,
        "ended_at": job.ended_at,
    }


@app.get("/stream/{job_id}")
async def stream_job(job_id: str, cursor: int = Query(default=0, ge=0)) -> StreamingResponse:
    job = jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")

    async def event_stream() -> AsyncIterator[str]:
        async for event in jobs.stream(job_id, cursor=cursor):
            yield _sse(event)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/git/status")
async def git_status(cwd_relative: str = ".") -> dict:
    try:
        cwd = resolve_cwd(config.root_dir, cwd_relative)
    except PathSecurityError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    result = await run_git(["status", "--short", "--branch"], cwd)
    return result


@app.post("/git/commit")
async def git_commit(req: CommitRequest) -> dict:
    if not config.write_enabled:
        raise HTTPException(status_code=403, detail="write operations are disabled")
    try:
        cwd = resolve_cwd(config.root_dir, req.cwd_relative)
    except PathSecurityError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if req.add_all:
        add_result = await run_git(["add", "-A"], cwd)
        if add_result["return_code"] != 0:
            return {"status": "failed", "step": "add", "result": add_result}
    commit_result = await run_git(["commit", "-m", req.message], cwd)
    status = "ok" if commit_result["return_code"] == 0 else "failed"
    return {"status": status, "result": commit_result}


@app.post("/git/push")
async def git_push(req: PushRequest) -> dict:
    if not config.write_enabled:
        raise HTTPException(status_code=403, detail="write operations are disabled")
    try:
        cwd = resolve_cwd(config.root_dir, req.cwd_relative)
    except PathSecurityError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    args = ["push", req.remote]
    if req.branch:
        args.append(req.branch)
    push_result = await run_git(args, cwd)
    status = "ok" if push_result["return_code"] == 0 else "failed"
    return {"status": status, "result": push_result}
