from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from collections.abc import AsyncIterator
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse

from .config import load_config
from .git_ops import run_git
from .job_manager import JobManager, build_command, parse_command_template
from .models import (
    AuthCodexDeviceStartRequest,
    AuthRuntimeKeysRequest,
    CommitRequest,
    PushRequest,
    RunRequest,
    RunResponse,
)
from .security import PathSecurityError, resolve_cwd

if sys.platform == "win32" and hasattr(asyncio, "WindowsProactorEventLoopPolicy"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

app = FastAPI(title="LoL Host Runner", version="0.1.0")
config = load_config()
jobs = JobManager()
AUTH_STATE_PATH = Path(os.getenv("RUNNER_AUTH_STATE_PATH", "/root/.lol_runner_auth.json"))
runtime_auth: dict[str, str] = {"openai_api_key": "", "gemini_api_key": ""}


def _load_runtime_auth() -> None:
    global runtime_auth
    if not AUTH_STATE_PATH.exists():
        return
    try:
        payload = json.loads(AUTH_STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return
    runtime_auth = {
        "openai_api_key": str(payload.get("openai_api_key") or ""),
        "gemini_api_key": str(payload.get("gemini_api_key") or ""),
    }


def _save_runtime_auth() -> None:
    AUTH_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    AUTH_STATE_PATH.write_text(json.dumps(runtime_auth, ensure_ascii=False), encoding="utf-8")


def _set_runtime_keys(openai_api_key: str | None, gemini_api_key: str | None, persist: bool) -> None:
    if openai_api_key is not None:
        runtime_auth["openai_api_key"] = openai_api_key.strip()
    if gemini_api_key is not None:
        runtime_auth["gemini_api_key"] = gemini_api_key.strip()
    if persist:
        _save_runtime_auth()


def _effective_openai_key() -> str:
    return (runtime_auth.get("openai_api_key") or "").strip() or (os.getenv("OPENAI_API_KEY") or "").strip()


def _effective_gemini_key() -> str:
    return (runtime_auth.get("gemini_api_key") or "").strip() or (os.getenv("GEMINI_API_KEY") or "").strip()


def _runner_ca_cert_file() -> str:
    return (os.getenv("RUNNER_CA_CERT_FILE") or "").strip()


def _runtime_env_overrides() -> dict[str, str]:
    env: dict[str, str] = {}
    openai_key = _effective_openai_key()
    gemini_key = _effective_gemini_key()
    ca_cert = _runner_ca_cert_file()
    if openai_key:
        env["OPENAI_API_KEY"] = openai_key
    if gemini_key:
        env["GEMINI_API_KEY"] = gemini_key
    if ca_cert and Path(ca_cert).exists():
        env["NODE_EXTRA_CA_CERTS"] = ca_cert
        env["SSL_CERT_FILE"] = ca_cert
        env["REQUESTS_CA_BUNDLE"] = ca_cert
    return env


_load_runtime_auth()


def _is_mock_source(source: str) -> bool:
    return "mock" in source.lower()


async def _codex_auth_ready() -> tuple[bool, str]:
    if _effective_openai_key():
        return True, "OPENAI_API_KEY present"
    try:
        result = await asyncio.to_thread(
            subprocess.run,
            ["codex", "login", "status"],
            capture_output=True,
            text=True,
            timeout=8,
        )
    except FileNotFoundError:
        return False, "codex command not found"
    except subprocess.TimeoutExpired:
        return False, "codex login status timed out"
    output = (result.stdout or result.stderr or "").strip()
    if result.returncode == 0:
        return True, output or "codex login status ok"
    return False, output or "not logged in"


def _gemini_settings_auth_ready() -> tuple[bool, str]:
    settings_path = Path.home() / ".gemini" / "settings.json"
    if not settings_path.exists():
        return False, "settings.json not found"
    try:
        payload = json.loads(settings_path.read_text(encoding="utf-8"))
    except Exception:
        return False, "settings.json unreadable"
    auth_keys = ("selectedAuthType", "authType", "authMethod", "auth_type", "auth_method")
    for key in auth_keys:
        value = payload.get(key)
        if value:
            return True, f"{key}={value}"
    return False, "auth type not configured in settings.json"


def _gemini_auth_ready() -> tuple[bool, str]:
    if _effective_gemini_key():
        return True, "GEMINI_API_KEY present"
    if (os.getenv("GOOGLE_GENAI_USE_VERTEXAI") or "").strip():
        return True, "GOOGLE_GENAI_USE_VERTEXAI enabled"
    if (os.getenv("GOOGLE_GENAI_USE_GCA") or "").strip():
        return True, "GOOGLE_GENAI_USE_GCA enabled"
    return _gemini_settings_auth_ready()


async def _build_preflight_payload(cwd: Path) -> dict:
    issues: list[dict[str, str]] = []
    checks: dict[str, object] = {
        "agent_mode": config.agent_mode,
        "codex_source": config.codex_source,
        "gemini_source": config.gemini_source,
        "codex_cli_available": config.codex_available,
        "gemini_cli_available": config.gemini_available,
        "codex_command_ready": bool(config.codex_cmd),
        "gemini_command_ready": bool(config.gemini_cmd),
        "openai_api_key_present": bool(_effective_openai_key()),
        "gemini_api_key_present": bool(_effective_gemini_key()),
        "runtime_openai_api_key_present": bool((runtime_auth.get("openai_api_key") or "").strip()),
        "runtime_gemini_api_key_present": bool((runtime_auth.get("gemini_api_key") or "").strip()),
        "runner_ca_cert_file": _runner_ca_cert_file(),
        "runner_ca_cert_exists": (not _runner_ca_cert_file()) or Path(_runner_ca_cert_file()).exists(),
    }

    if config.agent_mode == "mock":
        issues.append(
            {
                "code": "MOCK_MODE_ACTIVE",
                "message": "RUNNER_AGENT_MODE=mock is active. Real CLI mode is required.",
                "action": "Set RUNNER_AGENT_MODE=real and restart Docker Compose.",
            }
        )
    if _is_mock_source(config.codex_source):
        issues.append(
            {
                "code": "CODEX_MOCK_SOURCE",
                "message": f"codex source is `{config.codex_source}`.",
                "action": "Disable mock mode and use a real codex command.",
            }
        )
    if _is_mock_source(config.gemini_source):
        issues.append(
            {
                "code": "GEMINI_MOCK_SOURCE",
                "message": f"gemini source is `{config.gemini_source}`.",
                "action": "Disable mock mode and use a real gemini command.",
            }
        )

    if not config.codex_available:
        issues.append(
            {
                "code": "CODEX_CLI_MISSING",
                "message": "Codex CLI is not installed in runner container.",
                "action": "Install `@openai/codex` in runner image and rebuild containers.",
            }
        )
    if not config.gemini_available:
        issues.append(
            {
                "code": "GEMINI_CLI_MISSING",
                "message": "Gemini CLI is not installed in runner container.",
                "action": "Install `@google/gemini-cli` in runner image and rebuild containers.",
            }
        )
    if not config.codex_cmd:
        issues.append(
            {
                "code": "CODEX_CMD_UNRESOLVED",
                "message": "codex command template could not be resolved.",
                "action": "Set valid CODEX_CMD or ensure default codex CLI command is available.",
            }
        )
    if not config.gemini_cmd:
        issues.append(
            {
                "code": "GEMINI_CMD_UNRESOLVED",
                "message": "gemini command template could not be resolved.",
                "action": "Set valid GEMINI_CMD or ensure default gemini CLI command is available.",
            }
        )

    if _runner_ca_cert_file() and not Path(_runner_ca_cert_file()).exists():
        issues.append(
            {
                "code": "RUNNER_CA_CERT_MISSING",
                "message": f"RUNNER_CA_CERT_FILE not found: {_runner_ca_cert_file()}",
                "action": "Mount cert path into runner container or clear RUNNER_CA_CERT_FILE.",
            }
        )

    codex_auth_ready, codex_auth_detail = await _codex_auth_ready()
    checks["codex_auth_ready"] = codex_auth_ready
    checks["codex_auth_detail"] = codex_auth_detail
    if not codex_auth_ready:
        issues.append(
            {
                "code": "CODEX_AUTH_MISSING",
                "message": f"Codex auth is not ready ({codex_auth_detail}).",
                "action": "Set OPENAI_API_KEY or run `docker exec -it lol-runner codex login`.",
            }
        )
        lowered = codex_auth_detail.lower()
        if "certificate" in lowered or "self-signed" in lowered or "ssl" in lowered:
            issues.append(
                {
                    "code": "RUNNER_TLS_TRUST",
                    "message": "TLS trust chain issue detected for codex auth flow.",
                    "action": "Set RUNNER_CA_CERT_FILE and ensure the CA file is mounted in runner.",
                }
            )

    gemini_auth_ready, gemini_auth_detail = _gemini_auth_ready()
    checks["gemini_auth_ready"] = gemini_auth_ready
    checks["gemini_auth_detail"] = gemini_auth_detail
    if not gemini_auth_ready:
        issues.append(
            {
                "code": "GEMINI_AUTH_MISSING",
                "message": f"Gemini auth is not ready ({gemini_auth_detail}).",
                "action": (
                    "Set GEMINI_API_KEY (or GOOGLE_GENAI_USE_VERTEXAI/GOOGLE_GENAI_USE_GCA) "
                    "or configure /root/.gemini/settings.json."
                ),
            }
        )

    git_result = await run_git(["status", "--short", "--branch"], cwd)
    checks["git_status_return_code"] = int(git_result.get("return_code") or 0)
    if checks["git_status_return_code"] != 0:
        issues.append(
            {
                "code": "GIT_STATUS_FAILED",
                "message": f"git status failed ({checks['git_status_return_code']}).",
                "action": "Check RUNNER_ROOT_DIR and cwd_relative path mapping.",
            }
        )

    return {
        "ready": len(issues) == 0,
        "issues": issues,
        "checks": checks,
        "cwd": str(cwd),
        "health": {
            "root_dir": str(config.root_dir),
            "write_enabled": str(config.write_enabled),
            "agent_mode": config.agent_mode,
            "codex_source": config.codex_source,
            "gemini_source": config.gemini_source,
        },
        "git_status": git_result,
    }


async def _ensure_codex_ready_or_raise() -> None:
    if _is_mock_source(config.codex_source):
        raise HTTPException(
            status_code=412,
            detail="RUNNER_NOT_READY: codex is configured in mock mode; set RUNNER_AGENT_MODE=real.",
        )
    if not config.codex_available:
        raise HTTPException(
            status_code=412,
            detail="RUNNER_NOT_READY: codex CLI missing. Install @openai/codex and rebuild.",
        )
    if not config.codex_cmd:
        raise HTTPException(
            status_code=412,
            detail="RUNNER_NOT_READY: codex command unresolved. Set CODEX_CMD or install codex CLI.",
        )
    auth_ready, auth_detail = await _codex_auth_ready()
    if not auth_ready:
        raise HTTPException(
            status_code=412,
            detail=(
                "RUNNER_NOT_READY: codex auth missing "
                f"({auth_detail}). Set OPENAI_API_KEY or run `docker exec -it lol-runner codex login`."
            ),
        )


def _ensure_gemini_ready_or_raise() -> None:
    if _is_mock_source(config.gemini_source):
        raise HTTPException(
            status_code=412,
            detail="RUNNER_NOT_READY: gemini is configured in mock mode; set RUNNER_AGENT_MODE=real.",
        )
    if not config.gemini_available:
        raise HTTPException(
            status_code=412,
            detail="RUNNER_NOT_READY: gemini CLI missing. Install @google/gemini-cli and rebuild.",
        )
    if not config.gemini_cmd:
        raise HTTPException(
            status_code=412,
            detail="RUNNER_NOT_READY: gemini command unresolved. Set GEMINI_CMD or install gemini CLI.",
        )
    auth_ready, auth_detail = _gemini_auth_ready()
    if not auth_ready:
        raise HTTPException(
            status_code=412,
            detail=(
                "RUNNER_NOT_READY: gemini auth missing "
                f"({auth_detail}). Set GEMINI_API_KEY or configure /root/.gemini/settings.json."
            ),
        )


@app.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "ok",
        "root_dir": str(config.root_dir),
        "write_enabled": str(config.write_enabled),
        "agent_mode": config.agent_mode,
        "codex_source": config.codex_source,
        "gemini_source": config.gemini_source,
        "codex_available": str(config.codex_available),
        "gemini_available": str(config.gemini_available),
        "openai_api_key_present": str(bool(_effective_openai_key())),
        "gemini_api_key_present": str(bool(_effective_gemini_key())),
        "runtime_openai_api_key_present": str(bool((runtime_auth.get("openai_api_key") or "").strip())),
        "runtime_gemini_api_key_present": str(bool((runtime_auth.get("gemini_api_key") or "").strip())),
        "runner_ca_cert_file": _runner_ca_cert_file(),
        "runner_ca_cert_exists": str((not _runner_ca_cert_file()) or Path(_runner_ca_cert_file()).exists()),
    }


@app.get("/preflight/agents")
async def preflight_agents(cwd_relative: str = ".") -> dict:
    try:
        cwd = resolve_cwd(config.root_dir, cwd_relative)
    except PathSecurityError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return await _build_preflight_payload(cwd)


@app.get("/auth/urls")
async def auth_urls() -> dict:
    return {
        "codex_login_url": "https://platform.openai.com/login",
        "openai_api_keys_url": "https://platform.openai.com/settings/organization/api-keys",
        "gemini_login_url": "https://aistudio.google.com/",
        "gemini_api_keys_url": "https://aistudio.google.com/app/apikey",
    }


@app.get("/auth/runtime")
async def auth_runtime() -> dict:
    codex_ready, codex_detail = await _codex_auth_ready()
    gemini_ready, gemini_detail = _gemini_auth_ready()
    return {
        "codex": {
            "ready": codex_ready,
            "detail": codex_detail,
        },
        "gemini": {
            "ready": gemini_ready,
            "detail": gemini_detail,
        },
        "runtime_openai_api_key_present": bool((runtime_auth.get("openai_api_key") or "").strip()),
        "runtime_gemini_api_key_present": bool((runtime_auth.get("gemini_api_key") or "").strip()),
    }


@app.post("/auth/runtime-keys")
async def set_auth_runtime_keys(req: AuthRuntimeKeysRequest) -> dict:
    _set_runtime_keys(req.openai_api_key, req.gemini_api_key, persist=req.persist)
    codex_ready, codex_detail = await _codex_auth_ready()
    gemini_ready, gemini_detail = _gemini_auth_ready()
    return {
        "status": "ok",
        "persisted": bool(req.persist),
        "runtime_openai_api_key_present": bool((runtime_auth.get("openai_api_key") or "").strip()),
        "runtime_gemini_api_key_present": bool((runtime_auth.get("gemini_api_key") or "").strip()),
        "codex_ready": codex_ready,
        "codex_detail": codex_detail,
        "gemini_ready": gemini_ready,
        "gemini_detail": gemini_detail,
    }


@app.post("/auth/codex/device/start", response_model=RunResponse)
async def start_codex_device_auth(req: AuthCodexDeviceStartRequest) -> RunResponse:
    if not config.codex_available:
        raise HTTPException(status_code=412, detail="codex CLI is not available in runner container")
    cwd = config.root_dir
    job = await jobs.create(
        req.session_id,
        "codex-auth",
        cwd,
        ["codex", "login", "--device-auth"],
        prompt="codex device auth",
        env_overrides=_runtime_env_overrides(),
    )
    return RunResponse(job_id=job.job_id, status=job.status)


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


@app.post("/run/codex", response_model=RunResponse)
async def run_codex(req: RunRequest) -> RunResponse:
    try:
        cwd = resolve_cwd(config.root_dir, req.cwd_relative)
    except PathSecurityError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    explicit_template = bool(req.command_template and req.command_template.strip())
    if not explicit_template:
        await _ensure_codex_ready_or_raise()
    try:
        base_cmd = parse_command_template(req.command_template) if explicit_template else config.codex_cmd
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"invalid command_template: {exc}") from exc
    if not base_cmd:
        raise HTTPException(status_code=400, detail="invalid command_template: empty command")
    command = build_command(base_cmd, req.prompt, append_prompt_if_missing=not explicit_template)
    job = await jobs.create(
        req.session_id,
        "codex",
        cwd,
        command,
        req.prompt,
        env_overrides=_runtime_env_overrides(),
    )
    return RunResponse(job_id=job.job_id, status=job.status)


@app.post("/run/gemini", response_model=RunResponse)
async def run_gemini(req: RunRequest) -> RunResponse:
    try:
        cwd = resolve_cwd(config.root_dir, req.cwd_relative)
    except PathSecurityError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    explicit_template = bool(req.command_template and req.command_template.strip())
    if not explicit_template:
        _ensure_gemini_ready_or_raise()
    try:
        base_cmd = parse_command_template(req.command_template) if explicit_template else config.gemini_cmd
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"invalid command_template: {exc}") from exc
    if not base_cmd:
        raise HTTPException(status_code=400, detail="invalid command_template: empty command")
    command = build_command(base_cmd, req.prompt, append_prompt_if_missing=not explicit_template)
    job = await jobs.create(
        req.session_id,
        "gemini",
        cwd,
        command,
        req.prompt,
        env_overrides=_runtime_env_overrides(),
    )
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


@app.post("/jobs/{job_id}/cancel")
async def cancel_job(job_id: str) -> dict:
    job = jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    canceled = await jobs.terminate(job_id)
    return {
        "job_id": job_id,
        "canceled": canceled,
        "status": "canceled" if canceled else "not_running",
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
