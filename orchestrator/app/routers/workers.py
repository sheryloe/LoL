from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.models.schemas import WorkerRunRequest
from app.services.worker_service import worker_service

router = APIRouter(prefix="/api/projects/{project_id}/workers", tags=["workers"])


@router.get("")
def list_workers(project_id: str):
    return {"project_id": project_id, "workers": worker_service.list_workers()}


@router.get("/auth/status")
def worker_auth_status(project_id: str):
    return {"project_id": project_id, "status": worker_service.auth_status()}


@router.post("/{worker_name}/run")
def run_worker(project_id: str, worker_name: str, request: WorkerRunRequest):
    try:
        return worker_service.run_worker(project_id, worker_name, request)
    except RuntimeError as exc:
        raise HTTPException(status_code=412, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
