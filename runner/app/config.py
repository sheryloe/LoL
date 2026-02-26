from __future__ import annotations

import os
import shlex
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _cmd_from_raw(raw: str) -> list[str]:
    parts = shlex.split(raw)
    return [part for part in parts if part]


def _default_mock_cmd(role: str) -> list[str]:
    script = Path(__file__).resolve().parent / "mock_agent.py"
    return [sys.executable, str(script), role, "{prompt}"]


def _default_real_codex_cmd() -> list[str]:
    return ["codex", "exec", "--skip-git-repo-check", "--full-auto", "{prompt}"]


def _default_real_gemini_cmd() -> list[str]:
    return ["gemini", "--prompt", "{prompt}", "--yolo"]


def _normalize_mode(value: str | None) -> str:
    mode = (value or "auto").strip().lower()
    if mode in {"mock", "real", "auto"}:
        return mode
    return "auto"


def _has_command(binary: str) -> bool:
    return shutil.which(binary) is not None


@dataclass(frozen=True)
class RunnerConfig:
    root_dir: Path
    write_enabled: bool
    agent_mode: str
    codex_cmd: list[str]
    gemini_cmd: list[str]
    codex_source: str
    gemini_source: str
    codex_available: bool
    gemini_available: bool
    openai_api_key_present: bool
    gemini_api_key_present: bool


def load_config() -> RunnerConfig:
    root = Path(os.getenv("RUNNER_ROOT_DIR", r"D:\AI_Vibe\LoL")).resolve()
    agent_mode = _normalize_mode(os.getenv("RUNNER_AGENT_MODE"))
    codex_raw = (os.getenv("CODEX_CMD") or "").strip()
    gemini_raw = (os.getenv("GEMINI_CMD") or "").strip()
    openai_key_present = bool((os.getenv("OPENAI_API_KEY") or "").strip())
    gemini_key_present = bool((os.getenv("GEMINI_API_KEY") or "").strip())

    codex_available = _has_command("codex")
    gemini_available = _has_command("gemini")

    codex_cmd: list[str]
    gemini_cmd: list[str]
    codex_source: str
    gemini_source: str

    if codex_raw:
        codex_cmd = _cmd_from_raw(codex_raw)
        codex_source = "env:CODEX_CMD"
    elif agent_mode == "real":
        codex_cmd = _default_real_codex_cmd() if codex_available else _default_mock_cmd("codex")
        codex_source = "default:real" if codex_available else "fallback:mock_missing_codex"
    elif agent_mode == "mock":
        codex_cmd = _default_mock_cmd("codex")
        codex_source = "default:mock"
    else:
        if codex_available and openai_key_present:
            codex_cmd = _default_real_codex_cmd()
            codex_source = "default:auto_real"
        else:
            codex_cmd = _default_mock_cmd("codex")
            codex_source = "default:auto_mock"

    if gemini_raw:
        gemini_cmd = _cmd_from_raw(gemini_raw)
        gemini_source = "env:GEMINI_CMD"
    elif agent_mode == "real":
        gemini_cmd = _default_real_gemini_cmd() if gemini_available else _default_mock_cmd("gemini")
        gemini_source = "default:real" if gemini_available else "fallback:mock_missing_gemini"
    elif agent_mode == "mock":
        gemini_cmd = _default_mock_cmd("gemini")
        gemini_source = "default:mock"
    else:
        if gemini_available and gemini_key_present:
            gemini_cmd = _default_real_gemini_cmd()
            gemini_source = "default:auto_real"
        else:
            gemini_cmd = _default_mock_cmd("gemini")
            gemini_source = "default:auto_mock"

    return RunnerConfig(
        root_dir=root,
        write_enabled=_as_bool(os.getenv("RUNNER_WRITE_ENABLED"), default=False),
        agent_mode=agent_mode,
        codex_cmd=codex_cmd,
        gemini_cmd=gemini_cmd,
        codex_source=codex_source,
        gemini_source=gemini_source,
        codex_available=codex_available,
        gemini_available=gemini_available,
        openai_api_key_present=openai_key_present,
        gemini_api_key_present=gemini_key_present,
    )
