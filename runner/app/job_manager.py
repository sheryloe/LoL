from __future__ import annotations

import asyncio
import contextlib
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, AsyncGenerator


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def build_command(base_cmd: list[str], prompt: str) -> list[str]:
    command = [part.replace("{prompt}", prompt) for part in base_cmd]
    if not any("{prompt}" in part for part in base_cmd):
        command = [*command, prompt]
    return command


@dataclass
class Job:
    job_id: str
    session_id: str
    runner: str
    cwd: Path
    command: list[str]
    prompt: str
    status: str = "queued"
    return_code: int | None = None
    started_at: str | None = None
    ended_at: str | None = None
    events: list[dict[str, Any]] = field(default_factory=list)
    process: asyncio.subprocess.Process | None = None
    condition: asyncio.Condition = field(default_factory=asyncio.Condition)
    seq: int = 0


class JobManager:
    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._lock = asyncio.Lock()

    async def create(self, session_id: str, runner: str, cwd: Path, command: list[str], prompt: str) -> Job:
        job = Job(
            job_id=str(uuid.uuid4()),
            session_id=session_id,
            runner=runner,
            cwd=cwd,
            command=command,
            prompt=prompt,
        )
        async with self._lock:
            self._jobs[job.job_id] = job
        await self._emit(
            job,
            {
                "type": "meta",
                "event": "queued",
                "runner": job.runner,
                "command": job.command,
                "cwd": str(job.cwd),
                "timestamp": utc_now(),
            },
        )
        asyncio.create_task(self._run(job))
        return job

    def get(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    async def stream(self, job_id: str, cursor: int = 0) -> AsyncGenerator[dict[str, Any], None]:
        job = self.get(job_id)
        if job is None:
            return
        index = max(0, cursor)
        while True:
            async with job.condition:
                while index >= len(job.events) and job.status not in {"completed", "failed"}:
                    await job.condition.wait()
                while index < len(job.events):
                    event = job.events[index]
                    index += 1
                    yield event
                if job.status in {"completed", "failed"} and index >= len(job.events):
                    return

    async def _run(self, job: Job) -> None:
        try:
            job.status = "running"
            job.started_at = utc_now()
            await self._emit(
                job,
                {
                    "type": "meta",
                    "event": "started",
                    "timestamp": job.started_at,
                },
            )
            job.process = await asyncio.create_subprocess_exec(
                *job.command,
                cwd=str(job.cwd),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout_task = asyncio.create_task(self._pump(job, job.process.stdout, "stdout"))
            stderr_task = asyncio.create_task(self._pump(job, job.process.stderr, "stderr"))
            job.return_code = await job.process.wait()
            await asyncio.gather(stdout_task, stderr_task)
            job.status = "completed" if job.return_code == 0 else "failed"
            job.ended_at = utc_now()
            await self._emit(
                job,
                {
                    "type": "meta",
                    "event": "finished",
                    "status": job.status,
                    "return_code": job.return_code,
                    "timestamp": job.ended_at,
                },
            )
        except Exception as exc:  # pragma: no cover - defensive guard
            job.status = "failed"
            job.ended_at = utc_now()
            await self._emit(
                job,
                {
                    "type": "meta",
                    "event": "error",
                    "status": "failed",
                    "message": str(exc),
                    "timestamp": job.ended_at,
                },
            )

    async def _pump(
        self,
        job: Job,
        stream: asyncio.StreamReader | None,
        channel: str,
    ) -> None:
        if stream is None:
            return
        while True:
            line = await stream.readline()
            if not line:
                return
            text = line.decode(errors="replace").rstrip("\r\n")
            await self._emit(
                job,
                {
                    "type": "log",
                    "stream": channel,
                    "message": text,
                    "timestamp": utc_now(),
                },
            )

    async def _emit(self, job: Job, event: dict[str, Any]) -> None:
        async with job.condition:
            job.seq += 1
            payload = {"seq": job.seq, **event}
            job.events.append(payload)
            job.condition.notify_all()

    async def terminate(self, job_id: str) -> bool:
        job = self.get(job_id)
        if job is None or job.process is None:
            return False
        if job.process.returncode is not None:
            return False
        job.process.terminate()
        with contextlib.suppress(ProcessLookupError):
            await job.process.wait()
        return True

