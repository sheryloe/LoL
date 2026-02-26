from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path


def _run_git_sync(args: list[str], cwd: Path) -> dict:
    completed = subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return {
        "args": args,
        "cwd": str(cwd),
        "return_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


async def run_git(args: list[str], cwd: Path) -> dict:
    return await asyncio.to_thread(_run_git_sync, args, cwd)
