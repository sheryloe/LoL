from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _cmd_from_env(name: str, default: str) -> list[str]:
    raw = os.getenv(name, default).strip()
    return [part for part in raw.split(" ") if part]


@dataclass(frozen=True)
class RunnerConfig:
    root_dir: Path
    write_enabled: bool
    codex_cmd: list[str]
    gemini_cmd: list[str]


def load_config() -> RunnerConfig:
    root = Path(os.getenv("RUNNER_ROOT_DIR", r"D:\AI_Vibe\LoL")).resolve()
    return RunnerConfig(
        root_dir=root,
        write_enabled=_as_bool(os.getenv("RUNNER_WRITE_ENABLED"), default=False),
        codex_cmd=_cmd_from_env("CODEX_CMD", "codex"),
        gemini_cmd=_cmd_from_env("GEMINI_CMD", "gemini"),
    )

