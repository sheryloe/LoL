from __future__ import annotations

from pathlib import Path


class PathSecurityError(ValueError):
    """Raised when a path is not under root."""


def resolve_under_root(root_dir: Path, relative_path: str) -> Path:
    clean = (relative_path or ".").strip()
    if Path(clean).is_absolute():
        raise PathSecurityError("absolute paths are not allowed")
    if ":" in clean:
        raise PathSecurityError("drive-qualified paths are not allowed")
    candidate = (root_dir / clean).resolve()
    try:
        candidate.relative_to(root_dir.resolve())
    except ValueError as exc:
        raise PathSecurityError("path escapes root directory") from exc
    return candidate

