from __future__ import annotations

from datetime import datetime, timezone

from app.config import PROJECTS_ROOT
from app.models.schemas import ProjectCreateRequest, ProjectSummary
from app.utils.file_io import ensure_dir, list_files, read_json, read_text, write_json
from app.utils.paths import PROJECT_SUBDIRS, project_root, project_subdir, validate_project_id


class ProjectService:
    def list_projects(self) -> list[ProjectSummary]:
        projects: list[ProjectSummary] = []
        root = PROJECTS_ROOT

        if not root.exists():
            return projects

        for project_dir in root.iterdir():
            if not project_dir.is_dir():
                continue

            metadata_path = project_dir / "project.json"
            if not metadata_path.exists():
                continue

            data = read_json(metadata_path)
            if not data:
                continue

            try:
                created_at = datetime.fromisoformat(data["created_at"])
            except (KeyError, ValueError):
                created_at = datetime.fromtimestamp(project_dir.stat().st_mtime, tz=timezone.utc)

            projects.append(
                ProjectSummary(
                    project_id=data.get("project_id", project_dir.name),
                    title=data.get("title"),
                    created_at=created_at,
                )
            )

        projects.sort(key=lambda item: item.created_at, reverse=True)
        return projects

    def create_project(self, request: ProjectCreateRequest) -> ProjectSummary:
        project_id = validate_project_id(request.project_id)
        root = project_root(project_id)
        PROJECTS_ROOT.mkdir(parents=True, exist_ok=True)

        if root.exists():
            raise ValueError(f"project already exists: {project_id}")

        ensure_dir(root, request.write_enabled)
        for subdir in PROJECT_SUBDIRS:
            ensure_dir(root / subdir, request.write_enabled)

        created_at = datetime.now(tz=timezone.utc)
        metadata = {
            "project_id": project_id,
            "title": request.title,
            "created_at": created_at.isoformat(),
            "subdirs": PROJECT_SUBDIRS,
        }
        write_json(root / "project.json", metadata, request.write_enabled)

        return ProjectSummary(project_id=project_id, title=request.title, created_at=created_at)

    def get_project(self, project_id: str) -> dict:
        safe_project_id = validate_project_id(project_id)
        root = project_root(safe_project_id)
        if not root.exists():
            raise FileNotFoundError(f"project not found: {safe_project_id}")

        meta = read_json(root / "project.json")
        tabs: dict[str, list[dict]] = {}

        for subdir in PROJECT_SUBDIRS:
            tab_dir = project_subdir(safe_project_id, subdir)
            files = []
            for file_path in list_files(tab_dir, "*.md") + list_files(tab_dir, "*.json"):
                files.append(
                    {
                        "name": file_path.name,
                        "relative_path": str(file_path.relative_to(root)),
                        "content_preview": read_text(file_path)[:3000],
                        "updated_at": datetime.fromtimestamp(file_path.stat().st_mtime, tz=timezone.utc),
                    }
                )
            files.sort(key=lambda item: item["updated_at"], reverse=True)
            tabs[subdir] = files

        return {
            "project_id": safe_project_id,
            "title": meta.get("title"),
            "created_at": meta.get("created_at"),
            "tabs": tabs,
        }


project_service = ProjectService()
