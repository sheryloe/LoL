from __future__ import annotations

import shlex
from urllib.parse import urlencode

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError

from app.config import DOCKER_CONTAINER_NAME, NOTION_PARENT_PAGE_ID, NOTION_TOKEN, UI_ADMIN_TOKEN
from app.models.schemas import CoworkRunRequest, NotionPublishRequest, ProjectCreateRequest, WorkerRunRequest, WorkerTaskInput
from app.services.chat_service import chat_service
from app.services.cowork_service import cowork_service
from app.services.notion_service import notion_service
from app.services.project_service import project_service
from app.services.worker_service import worker_service

router = APIRouter(tags=["ui"])
templates = Jinja2Templates(directory="templates")


def _validation_message(exc: ValidationError) -> str:
    errors = exc.errors()
    if not errors:
        return "입력값 검증에 실패했습니다."

    first = errors[0]
    field = ".".join(str(part) for part in first.get("loc", []))
    message = str(first.get("msg", "입력값이 올바르지 않습니다."))

    if field == "project_id":
        return "프로젝트 ID는 3~64자이며 영문/숫자/밑줄(_)과 하이픈(-)만 허용됩니다."
    if field == "notion_token":
        return "Notion Token을 입력해 주세요. (또는 환경변수 NOTION_TOKEN 설정)"
    if field == "parent_page_id":
        return "Notion Parent Page ID를 입력해 주세요. (32~36자 UUID)"

    return f"{field}: {message}" if field else message


def _humanize_error(message: str) -> str:
    if message.startswith("project_id must be 3-64 chars"):
        return "프로젝트 ID는 3~64자이며 영문/숫자/밑줄(_)과 하이픈(-)만 허용됩니다."
    if message.startswith("project already exists"):
        return "이미 존재하는 프로젝트 ID입니다."
    if message.startswith("write operation blocked"):
        return "쓰기 작업이 차단되었습니다. '쓰기 허용' 체크 + 올바른 Admin Token을 입력하세요."
    if "parent_page_id must be a Notion page id" in message:
        return "Notion Parent Page ID 형식이 올바르지 않습니다. (32~36자 UUID)"
    if message.startswith("notion token is required"):
        return "Notion Token이 비어 있습니다."
    if message.startswith("notion publish failed: status=400"):
        return "Notion API 400 Bad Request: 자동 재시도 후에도 실패했습니다. 입력값을 확인해 주세요."
    if "codex CLI login is required" in message:
        return (
            "Codex CLI 로그인 필요: "
            f"docker exec -it {DOCKER_CONTAINER_NAME} codex login --device-auth"
        )
    if "gemini CLI login is required" in message:
        return (
            "Gemini CLI 로그인 필요: "
            f"docker exec -it {DOCKER_CONTAINER_NAME} gemini 실행 후 /auth 입력"
        )
    return message


def _redirect_with_error(base_path: str, message: str) -> RedirectResponse:
    query = urlencode({"error": message})
    return RedirectResponse(url=f"{base_path}?{query}", status_code=303)


def _redirect_with_info(base_path: str, message: str) -> RedirectResponse:
    query = urlencode({"info": message})
    return RedirectResponse(url=f"{base_path}?{query}", status_code=303)


@router.get("/")
def home(request: Request, error: str | None = None, info: str | None = None):
    projects = project_service.list_projects()
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "projects": projects,
            "error": error,
            "info": info,
        },
    )


@router.get("/projects/{project_id}")
def project_detail(request: Request, project_id: str, error: str | None = None, info: str | None = None):
    try:
        project = project_service.get_project(project_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return templates.TemplateResponse(
        "project.html",
        {
            "request": request,
            "project": project,
            "workers": worker_service.list_workers(),
            "worker_auth_status": worker_service.auth_status(),
            "latest_session": chat_service.get_session(project_id),
            "sessions": chat_service.list_sessions(project_id),
            "error": error,
            "info": info,
            "default_notion_parent_page_id": NOTION_PARENT_PAGE_ID,
        },
    )


@router.post("/ui/projects/create")
def create_project_ui(
    project_id: str = Form(...),
    title: str = Form(default=""),
    write_enabled: bool = Form(default=False),
    admin_token: str = Form(default=""),
):
    try:
        effective_write = write_enabled and admin_token == UI_ADMIN_TOKEN
        payload = ProjectCreateRequest(
            project_id=project_id,
            title=title or None,
            write_enabled=effective_write,
        )
        project_service.create_project(payload)
    except ValidationError as exc:
        return _redirect_with_error("/", _validation_message(exc))
    except PermissionError as exc:
        return _redirect_with_error("/", _humanize_error(str(exc)))
    except ValueError as exc:
        return _redirect_with_error("/", _humanize_error(str(exc)))

    return RedirectResponse(url=f"/projects/{project_id}", status_code=303)


@router.post("/ui/projects/{project_id}/run")
def run_worker_ui(
    project_id: str,
    worker_name: str = Form(...),
    prompt: str = Form(...),
    model: str = Form(default=""),
    cli_args: str = Form(default=""),
    write_enabled: bool = Form(default=False),
    admin_token: str = Form(default=""),
):
    try:
        effective_write = write_enabled and admin_token == UI_ADMIN_TOKEN
        args = shlex.split(cli_args) if cli_args.strip() else []
        req = WorkerRunRequest(
            task=WorkerTaskInput(prompt=prompt, model=model or None, cli_args=args),
            write_enabled=effective_write,
        )
        worker_service.run_worker(project_id=project_id, worker_name=worker_name, request=req)
    except ValidationError as exc:
        return _redirect_with_error(f"/projects/{project_id}", _validation_message(exc))
    except PermissionError as exc:
        return _redirect_with_error(f"/projects/{project_id}", _humanize_error(str(exc)))
    except RuntimeError as exc:
        return _redirect_with_error(f"/projects/{project_id}", _humanize_error(str(exc)))
    except FileNotFoundError as exc:
        return _redirect_with_error("/", _humanize_error(str(exc)))
    except ValueError as exc:
        return _redirect_with_error(f"/projects/{project_id}", _humanize_error(str(exc)))

    return RedirectResponse(url=f"/projects/{project_id}", status_code=303)


@router.post("/ui/projects/{project_id}/cowork/run")
def run_cowork_ui(
    project_id: str,
    prompt: str = Form(...),
    session_id: str = Form(default=""),
    rounds: int = Form(default=1),
    order: str = Form(default="codex_then_gemini"),
    codex_cli_args: str = Form(default=""),
    gemini_cli_args: str = Form(default=""),
    write_enabled: bool = Form(default=False),
    admin_token: str = Form(default=""),
):
    try:
        effective_write = write_enabled and admin_token == UI_ADMIN_TOKEN
        req = CoworkRunRequest(
            prompt=prompt,
            session_id=session_id or None,
            rounds=rounds,
            order=order,
            codex_cli_args=shlex.split(codex_cli_args) if codex_cli_args.strip() else [],
            gemini_cli_args=shlex.split(gemini_cli_args) if gemini_cli_args.strip() else [],
            write_enabled=effective_write,
        )
        result = cowork_service.run(project_id=project_id, request=req)
        return _redirect_with_info(
            f"/projects/{project_id}",
            (
                "협업 실행 완료: "
                f"session={result.get('session_id')} "
                f"rounds={result.get('rounds')} "
                f"turns={result.get('turn_count')}"
            ),
        )
    except ValidationError as exc:
        return _redirect_with_error(f"/projects/{project_id}", _validation_message(exc))
    except PermissionError as exc:
        return _redirect_with_error(f"/projects/{project_id}", _humanize_error(str(exc)))
    except RuntimeError as exc:
        return _redirect_with_error(f"/projects/{project_id}", _humanize_error(str(exc)))
    except FileNotFoundError as exc:
        return _redirect_with_error("/", _humanize_error(str(exc)))
    except ValueError as exc:
        return _redirect_with_error(f"/projects/{project_id}", _humanize_error(str(exc)))


@router.post("/ui/projects/{project_id}/notion/publish")
def publish_notion_ui(
    project_id: str,
    notion_token: str = Form(default=""),
    parent_page_id: str = Form(default=""),
    step_title: str = Form(...),
    one_line_summary: str = Form(...),
    background: str = Form(...),
    core_concepts: str = Form(...),
    implementation_details: str = Form(...),
    test_notes: str = Form(...),
    troubleshooting: str = Form(default=""),
    next_steps: str = Form(...),
):
    try:
        project_service.get_project(project_id)
        payload = NotionPublishRequest(
            notion_token=notion_token.strip() or NOTION_TOKEN,
            parent_page_id=parent_page_id.strip() or NOTION_PARENT_PAGE_ID,
            step_title=step_title,
            one_line_summary=one_line_summary,
            background=background,
            core_concepts=core_concepts,
            implementation_details=implementation_details,
            test_notes=test_notes,
            troubleshooting=troubleshooting,
            next_steps=next_steps,
        )

        markdown = notion_service.build_step_markdown(
            project_id=project_id,
            step_title=payload.step_title,
            one_line_summary=payload.one_line_summary,
            background=payload.background,
            core_concepts=payload.core_concepts,
            implementation_details=payload.implementation_details,
            test_notes=payload.test_notes,
            troubleshooting=payload.troubleshooting,
            next_steps=payload.next_steps,
        )

        result = notion_service.publish_markdown(
            notion_token=payload.notion_token,
            parent_page_id=payload.parent_page_id,
            page_title=f"[{project_id}] {payload.step_title}",
            markdown=markdown,
        )
        page_url = result.get("page_url") or "(url unavailable)"
        retries = result.get("bad_request_retries", 0)
        return _redirect_with_info(
            f"/projects/{project_id}",
            f"Notion page published: {page_url} (400-retries={retries})",
        )
    except ValidationError as exc:
        return _redirect_with_error(f"/projects/{project_id}", _validation_message(exc))
    except (ValueError, RuntimeError) as exc:
        return _redirect_with_error(f"/projects/{project_id}", _humanize_error(str(exc)))
