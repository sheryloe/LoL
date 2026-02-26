from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def ensure_write_enabled(write_enabled: bool) -> None:
    if not write_enabled:
        raise PermissionError("write operation blocked: set write_enabled=true")


def ensure_dir(path: Path, write_enabled: bool) -> None:
    ensure_write_enabled(write_enabled)
    path.mkdir(parents=True, exist_ok=True)


def write_text(path: Path, content: str, write_enabled: bool) -> None:
    ensure_write_enabled(write_enabled)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(content, encoding="utf-8")
    tmp_path.replace(path)


def write_json(path: Path, payload: Any, write_enabled: bool) -> None:
    content = json.dumps(payload, indent=2, ensure_ascii=False)
    write_text(path, content + "\n", write_enabled)


def read_text(path: Path) -> str:
    if not path.exists() or not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists() or not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def list_files(path: Path, pattern: str = "*") -> list[Path]:
    if not path.exists() or not path.is_dir():
        return []
    return sorted([p for p in path.glob(pattern) if p.is_file()], key=lambda p: p.name)
