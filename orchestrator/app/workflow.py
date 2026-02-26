from __future__ import annotations

import asyncio
import re
import uuid
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from .journal import JournalStore
from .models import ChatRequest
from .runner_client import RunnerClient


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class StepResult:
    step: str
    runner: str
    output: str
    return_code: int
    status: str


@dataclass
class WorkflowJob:
    workflow_job_id: str
    session_id: str
    cwd_relative: str
    user_message: str
    enable_fix: bool
    status: str = "queued"
    started_at: str | None = None
    ended_at: str | None = None
    seq: int = 0
    events: list[dict[str, Any]] = field(default_factory=list)
    condition: asyncio.Condition = field(default_factory=asyncio.Condition)
    artifacts: dict[str, str] = field(default_factory=dict)


class WorkflowManager:
    def __init__(self, runner: RunnerClient, journal: JournalStore) -> None:
        self.runner = runner
        self.journal = journal
        self._jobs: dict[str, WorkflowJob] = {}
        self._lock = asyncio.Lock()

    async def start(self, req: ChatRequest) -> WorkflowJob:
        job = WorkflowJob(
            workflow_job_id=str(uuid.uuid4()),
            session_id=req.session_id,
            cwd_relative=req.cwd_relative,
            user_message=req.message,
            enable_fix=req.enable_fix,
        )
        async with self._lock:
            self._jobs[job.workflow_job_id] = job
        await self._emit(
            job,
            {
                "type": "meta",
                "event": "queued",
                "status": job.status,
            },
        )
        asyncio.create_task(self._execute(job))
        return job

    def get(self, workflow_job_id: str) -> WorkflowJob | None:
        return self._jobs.get(workflow_job_id)

    async def stream(self, workflow_job_id: str, cursor: int = 0) -> AsyncGenerator[dict[str, Any], None]:
        job = self.get(workflow_job_id)
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

    async def _execute(self, job: WorkflowJob) -> None:
        job.status = "running"
        job.started_at = utc_now()
        await self._emit(
            job,
            {"type": "meta", "event": "started", "status": job.status, "started_at": job.started_at},
        )
        try:
            plan_prompt = self._build_plan_prompt(job.user_message)
            plan_result = await self._run_agent_step(job, "plan", "gemini", plan_prompt)
            self._save_artifact(job, "plan", self._extract_section(plan_result.output, "Plan"))
            self._save_artifact(job, "tasks", self._extract_section(plan_result.output, "Tasks"))

            impl_prompt = self._build_implement_prompt(job.user_message, plan_result.output)
            impl_result = await self._run_agent_step(job, "implement", "codex", impl_prompt)
            self._save_artifact(job, "patch", self._extract_section(impl_result.output, "Patch"))
            self._save_artifact(job, "files", self._extract_section(impl_result.output, "Files"))

            review_prompt = self._build_review_prompt(job.user_message, plan_result.output, impl_result.output)
            review_result = await self._run_agent_step(job, "review", "gemini", review_prompt)
            review_section = self._extract_section(review_result.output, "Review")
            if not review_section.strip():
                review_section = review_result.output
            self._save_artifact(job, "review", review_section)

            verdict = self._parse_verdict(review_result.output)
            await self._emit(
                job,
                {"type": "meta", "event": "review_verdict", "verdict": verdict},
            )
            if verdict == "FAIL" and job.enable_fix:
                fix_prompt = self._build_fix_prompt(job.user_message, impl_result.output, review_result.output)
                fix_result = await self._run_agent_step(job, "fix", "codex", fix_prompt)
                self._save_artifact(job, "patch", self._extract_section(fix_result.output, "Patch"))
                self._save_artifact(job, "files", self._extract_section(fix_result.output, "Files"))

            git_status = await self.runner.git_status(job.cwd_relative)
            self._save_artifact(job, "git", git_status.get("stdout", ""))
            await self._emit(
                job,
                {
                    "type": "artifact",
                    "name": "git",
                    "content": git_status.get("stdout", ""),
                },
            )

            job.status = "completed"
            job.ended_at = utc_now()
            await self._emit(
                job,
                {"type": "meta", "event": "finished", "status": job.status, "ended_at": job.ended_at},
            )
        except Exception as exc:  # pragma: no cover - runtime guard
            job.status = "failed"
            job.ended_at = utc_now()
            await self._emit(
                job,
                {
                    "type": "meta",
                    "event": "error",
                    "status": "failed",
                    "message": str(exc),
                    "ended_at": job.ended_at,
                },
            )

    async def _run_agent_step(self, job: WorkflowJob, step: str, runner: str, prompt: str) -> StepResult:
        await self._emit(
            job,
            {"type": "step", "event": "start", "step": step, "runner": runner},
        )
        runner_job_id = await self.runner.start_job(runner, job.session_id, prompt, job.cwd_relative)
        await self._emit(
            job,
            {"type": "step", "event": "runner_job_created", "step": step, "runner": runner, "runner_job_id": runner_job_id},
        )

        output_lines: list[str] = []
        async for event in self.runner.stream_job(runner_job_id):
            if event.get("type") == "log":
                message = event.get("message", "")
                output_lines.append(message)
            await self._emit(
                job,
                {"type": "runner_event", "step": step, "runner": runner, "payload": event},
            )

        status_payload = await self.runner.get_job(runner_job_id)
        return_code = int(status_payload.get("return_code") or 0)
        status = str(status_payload.get("status") or "failed")
        output = "\n".join(output_lines).strip()
        if not output:
            output = "(no output)"
        await self._emit(
            job,
            {
                "type": "step",
                "event": "finish",
                "step": step,
                "runner": runner,
                "status": status,
                "return_code": return_code,
            },
        )
        await self._emit(
            job,
            {
                "type": "artifact",
                "name": step,
                "content": output,
            },
        )
        if return_code != 0:
            raise RuntimeError(f"{runner} {step} failed with code {return_code}")
        return StepResult(step=step, runner=runner, output=output, return_code=return_code, status=status)

    async def _emit(self, job: WorkflowJob, event: dict[str, Any]) -> None:
        async with job.condition:
            job.seq += 1
            payload = {"seq": job.seq, "timestamp": utc_now(), **event}
            job.events.append(payload)
            job.condition.notify_all()
        await self.journal.append(job.session_id, {"workflow_job_id": job.workflow_job_id, **payload})

    def _save_artifact(self, job: WorkflowJob, name: str, content: str) -> None:
        if content.strip():
            job.artifacts[name] = content

    @staticmethod
    def _extract_section(text: str, section_name: str) -> str:
        pattern = re.compile(
            rf"(?ims)^#+\s*{re.escape(section_name)}\s*$\n(.*?)(?=^#|\Z)",
        )
        match = pattern.search(text)
        return match.group(1).strip() if match else ""

    @staticmethod
    def _parse_verdict(text: str) -> str:
        match = re.search(r"(?im)^\s*VERDICT\s*:\s*(PASS|FAIL)\s*$", text)
        return match.group(1).upper() if match else "PASS"

    @staticmethod
    def _build_plan_prompt(user_message: str) -> str:
        return (
            "You are Gemini in planning mode.\n"
            "Create implementation plan for the user's request.\n"
            "Output markdown sections exactly:\n"
            "# Plan\n"
            "# Tasks\n\n"
            f"User request:\n{user_message}\n"
        )

    @staticmethod
    def _build_implement_prompt(user_message: str, plan_output: str) -> str:
        return (
            "You are Codex implementation agent.\n"
            "Implement based on plan and summarize key changes.\n"
            "Output markdown sections exactly:\n"
            "# Summary\n"
            "# Patch\n"
            "# Files\n\n"
            f"User request:\n{user_message}\n\n"
            f"Plan:\n{plan_output}\n"
        )

    @staticmethod
    def _build_review_prompt(user_message: str, plan_output: str, implement_output: str) -> str:
        return (
            "You are Gemini reviewer.\n"
            "Review the implementation against user request and plan.\n"
            "Output markdown with line 1 as `VERDICT: PASS` or `VERDICT: FAIL`.\n"
            "Then sections:\n"
            "# Review\n"
            "# Risks\n"
            "# Suggested Fix\n\n"
            f"User request:\n{user_message}\n\n"
            f"Plan:\n{plan_output}\n\n"
            f"Implementation output:\n{implement_output}\n"
        )

    @staticmethod
    def _build_fix_prompt(user_message: str, implement_output: str, review_output: str) -> str:
        return (
            "You are Codex fix agent.\n"
            "Apply only fixes requested in review.\n"
            "Output markdown sections exactly:\n"
            "# Summary\n"
            "# Patch\n"
            "# Files\n\n"
            f"User request:\n{user_message}\n\n"
            f"Current implementation summary:\n{implement_output}\n\n"
            f"Review requiring fixes:\n{review_output}\n"
        )

