from __future__ import annotations

from app.models.schemas import WorkerRunRequest, WorkerResult
from app.services.cli_auth_service import cli_auth_service
from app.services.project_service import project_service
from app.workers.codex_worker import CodexWorker
from app.workers.gemini_worker import GeminiWorker
from app.workers.ollama_worker import OllamaWorker


class WorkerService:
    def __init__(self) -> None:
        self._workers = {
            "ollama": OllamaWorker(),
            "codex": CodexWorker(),
            "gemini": GeminiWorker(),
        }

    def list_workers(self) -> list[str]:
        return sorted(self._workers.keys())

    def auth_status(self) -> dict:
        return cli_auth_service.summary()

    def run_worker(self, project_id: str, worker_name: str, request: WorkerRunRequest) -> WorkerResult:
        project_service.get_project(project_id)

        key = worker_name.lower().strip()
        if key not in self._workers:
            available = ", ".join(self.list_workers())
            raise ValueError(f"unknown worker: {worker_name}. available: {available}")

        if key in {"codex", "gemini"}:
            cli_auth_service.ensure_ready(key)

        worker = self._workers[key]
        return worker.execute(project_id=project_id, task=request.task, write_enabled=request.write_enabled)


worker_service = WorkerService()
