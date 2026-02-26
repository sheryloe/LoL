from __future__ import annotations

import abc
from datetime import datetime, timezone

from app.models.schemas import WorkerResult, WorkerTaskInput
from app.utils.file_io import ensure_write_enabled, write_json, write_text
from app.utils.paths import project_subdir


class BaseWorker(abc.ABC):
    name: str = "base"
    output_subdir: str = "artifacts"

    def execute(self, project_id: str, task: WorkerTaskInput, write_enabled: bool) -> WorkerResult:
        ensure_write_enabled(write_enabled)

        started_at = datetime.now(tz=timezone.utc)
        timestamp = started_at.strftime("%Y%m%d_%H%M%S")

        success = True
        error: str | None = None
        stdout = ""
        stderr = ""

        try:
            run_payload = self._run(task)
            stdout = str(run_payload.get("stdout", "") or "")
            stderr = str(run_payload.get("stderr", "") or "")
            markdown_body = str(run_payload.get("markdown", "") or "")
        except Exception as exc:  # noqa: BLE001
            success = False
            error = str(exc)
            markdown_body = f"# {self.name} execution failed\n\n```\n{error}\n```\n"

        finished_at = datetime.now(tz=timezone.utc)

        output_dir = project_subdir(project_id, self.output_subdir)
        artifact_dir = project_subdir(project_id, "artifacts")
        output_filename = f"{timestamp}_{self.name}.md"
        metadata_filename = f"{timestamp}_{self.name}.json"

        output_path = output_dir / output_filename
        metadata_path = artifact_dir / metadata_filename

        write_text(output_path, markdown_body, write_enabled)

        metadata = {
            "worker": self.name,
            "project_id": project_id,
            "success": success,
            "error": error,
            "stdout": stdout,
            "stderr": stderr,
            "started_at": started_at.isoformat(),
            "finished_at": finished_at.isoformat(),
            "output_path": str(output_path),
        }
        write_json(metadata_path, metadata, write_enabled)

        return WorkerResult(
            worker=self.name,
            success=success,
            output_path=str(output_path),
            metadata_path=str(metadata_path),
            stdout=stdout,
            stderr=stderr,
            error=error,
            started_at=started_at,
            finished_at=finished_at,
        )

    @abc.abstractmethod
    def _run(self, task: WorkerTaskInput) -> dict[str, str]:
        raise NotImplementedError
