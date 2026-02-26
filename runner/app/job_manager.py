from __future__ import annotations

import asyncio
import contextlib
import os
import queue
import shlex
import subprocess
import threading
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, AsyncGenerator


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def build_command(base_cmd: list[str], prompt: str, append_prompt_if_missing: bool = True) -> list[str]:
    command = [part.replace("{prompt}", prompt) for part in base_cmd]
    if append_prompt_if_missing and not any("{prompt}" in part for part in base_cmd):
        command = [*command, prompt]
    return command


def parse_command_template(raw_template: str) -> list[str]:
    parts = shlex.split(raw_template.strip())
    return [part for part in parts if part]


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
    process: subprocess.Popen[str] | None = None
    condition: asyncio.Condition = field(default_factory=asyncio.Condition)
    seq: int = 0
    env_overrides: dict[str, str] = field(default_factory=dict)


class JobManager:
    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._lock = asyncio.Lock()

    async def create(
        self,
        session_id: str,
        runner: str,
        cwd: Path,
        command: list[str],
        prompt: str,
        env_overrides: dict[str, str] | None = None,
    ) -> Job:
        job = Job(
            job_id=str(uuid.uuid4()),
            session_id=session_id,
            runner=runner,
            cwd=cwd,
            command=command,
            prompt=prompt,
            env_overrides=dict(env_overrides or {}),
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
            # Use stdlib subprocess for cross-platform stability (Windows asyncio loop can
            # raise NotImplementedError for create_subprocess_exec).
            job.process = subprocess.Popen(
                job.command,
                cwd=str(job.cwd),
                env={**os.environ, **job.env_overrides},
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            )

            line_queue: queue.Queue[tuple[str, str | None]] = queue.Queue()

            def _reader(stream, channel: str) -> None:
                try:
                    if stream is None:
                        return
                    for raw_line in iter(stream.readline, ""):
                        line_queue.put((channel, raw_line.rstrip("\r\n")))
                finally:
                    line_queue.put((channel, None))

            stdout_thread = threading.Thread(
                target=_reader,
                args=(job.process.stdout, "stdout"),
                daemon=True,
            )
            stderr_thread = threading.Thread(
                target=_reader,
                args=(job.process.stderr, "stderr"),
                daemon=True,
            )
            stdout_thread.start()
            stderr_thread.start()

            open_streams = {"stdout": True, "stderr": True}
            while any(open_streams.values()):
                try:
                    channel, line = line_queue.get(timeout=0.1)
                except queue.Empty:
                    await asyncio.sleep(0.05)
                    continue
                if line is None:
                    open_streams[channel] = False
                    continue
                await self._emit(
                    job,
                    {
                        "type": "log",
                        "stream": channel,
                        "message": line,
                        "timestamp": utc_now(),
                    },
                )

            stdout_thread.join(timeout=1.0)
            stderr_thread.join(timeout=1.0)
            job.return_code = job.process.wait()
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
            error_message = f"{exc.__class__.__name__}: {exc}" if str(exc) else exc.__class__.__name__
            await self._emit(
                job,
                {
                    "type": "meta",
                    "event": "error",
                    "status": "failed",
                    "message": error_message,
                    "timestamp": job.ended_at,
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
        if job.process.poll() is not None:
            return False
        job.process.terminate()
        with contextlib.suppress(ProcessLookupError):
            await asyncio.to_thread(job.process.wait, 5)
        return True
