from __future__ import annotations

from pathlib import Path


class PathSecurityError(ValueError):
    """Raised when a path escapes the configured root directory."""


def ensure_within_root(root_dir: Path, candidate: Path) -> Path:
    root_resolved = root_dir.resolve()
    cand_resolved = candidate.resolve()
    try:
        cand_resolved.relative_to(root_resolved)
    except ValueError as exc:
        raise PathSecurityError(f"path is outside root: {cand_resolved}") from exc
    return cand_resolved


def resolve_cwd(root_dir: Path, cwd_relative: str) -> Path:
    clean = (cwd_relative or ".").strip()
    if Path(clean).is_absolute():
        raise PathSecurityError("absolute cwd paths are not allowed")
    if ":" in clean:
        raise PathSecurityError("drive-qualified paths are not allowed")
    candidate = root_dir / clean
    return ensure_within_root(root_dir, candidate)

