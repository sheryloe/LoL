from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.models.schemas import CoworkRunRequest, NotionPublishRequest, ProjectCreateRequest
from app.services.cowork_service import cowork_service
from app.services.project_service import project_service
from app.services.notion_service import notion_service

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("")
def list_projects():
    return project_service.list_projects()


@router.post("")
def create_project(request: ProjectCreateRequest):
    try:
        return project_service.create_project(request)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{project_id}")
def get_project(project_id: str):
    try:
        return project_service.get_project(project_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{project_id}/notion/publish")
def publish_project_step_to_notion(project_id: str, request: NotionPublishRequest):
    try:
        project_service.get_project(project_id)
        markdown = notion_service.build_step_markdown(
            project_id=project_id,
            step_title=request.step_title,
            one_line_summary=request.one_line_summary,
            background=request.background,
            core_concepts=request.core_concepts,
            implementation_details=request.implementation_details,
            test_notes=request.test_notes,
            troubleshooting=request.troubleshooting,
            next_steps=request.next_steps,
        )
        return notion_service.publish_markdown(
            notion_token=request.notion_token,
            parent_page_id=request.parent_page_id,
            page_title=f"[{project_id}] {request.step_title}",
            markdown=markdown,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/{project_id}/cowork/run")
def run_cowork(project_id: str, request: CoworkRunRequest):
    try:
        return cowork_service.run(project_id=project_id, request=request)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=412, detail=str(exc)) from exc
