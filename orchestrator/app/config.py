from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class OrchestratorConfig:
    runner_base_url: str
    root_dir: Path
    data_dir: Path
    journal_dir: Path
    projects_dir: Path


def load_config() -> OrchestratorConfig:
    data_dir = Path(os.getenv("ORCH_DATA_DIR", "/app/data")).resolve()
    root_dir = Path(os.getenv("ORCH_ROOT_DIR", "/workspace/LoL")).resolve()
    journal_dir = (data_dir / "journals").resolve()
    projects_dir = (data_dir / "projects").resolve()
    journal_dir.mkdir(parents=True, exist_ok=True)
    projects_dir.mkdir(parents=True, exist_ok=True)
    return OrchestratorConfig(
        runner_base_url=os.getenv("RUNNER_BASE_URL", "http://host.docker.internal:8765").rstrip("/"),
        root_dir=root_dir,
        data_dir=data_dir,
        journal_dir=journal_dir,
        projects_dir=projects_dir,
    )
