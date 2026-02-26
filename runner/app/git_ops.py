from __future__ import annotations

import asyncio
from pathlib import Path


async def run_git(args: list[str], cwd: Path) -> dict:
    process = await asyncio.create_subprocess_exec(
        "git",
        *args,
        cwd=str(cwd),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout_raw, stderr_raw = await process.communicate()
    stdout = stdout_raw.decode(errors="replace")
    stderr = stderr_raw.decode(errors="replace")
    return {
        "args": args,
        "cwd": str(cwd),
        "return_code": process.returncode,
        "stdout": stdout,
        "stderr": stderr,
    }

