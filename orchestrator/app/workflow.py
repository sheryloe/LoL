from __future__ import annotations

import asyncio
import re
import uuid
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from .conversations import ProjectConversationStore
from .journal import JournalStore
from .models import PipelineStep, ResolvedChatRequest
from .run_store import WorkflowRunStore
from .runner_client import RunnerClient


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


class WorkflowCanceled(Exception):
    pass


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
    project_id: str
    session_id: str
    cwd_relative: str
    user_message: str
    enable_fix: bool
    codex_cmd_template: str
    gemini_cmd_template: str
    pipeline_steps: list[PipelineStep]
    status: str = "queued"
    started_at: str | None = None
    ended_at: str | None = None
    seq: int = 0
    events: list[dict[str, Any]] = field(default_factory=list)
    condition: asyncio.Condition = field(default_factory=asyncio.Condition)
    artifacts: dict[str, str] = field(default_factory=dict)
    runner_job_ids: list[str] = field(default_factory=list)
    cancel_requested: bool = False


class WorkflowManager:
    def __init__(
        self,
        runner: RunnerClient,
        journal: JournalStore,
        conversation_store: ProjectConversationStore,
        run_store: WorkflowRunStore,
    ) -> None:
        self.runner = runner
        self.journal = journal
        self.conversation_store = conversation_store
        self.run_store = run_store
        self._jobs: dict[str, WorkflowJob] = {}
        self._lock = asyncio.Lock()

    async def start(self, req: ResolvedChatRequest) -> WorkflowJob:
        job = WorkflowJob(
            workflow_job_id=str(uuid.uuid4()),
            project_id=req.project_id,
            session_id=req.session_id,
            cwd_relative=req.cwd_relative,
            user_message=req.message,
            enable_fix=req.enable_fix,
            codex_cmd_template=req.codex_cmd_template,
            gemini_cmd_template=req.gemini_cmd_template,
            pipeline_steps=list(req.pipeline_steps),
        )
        async with self._lock:
            self._jobs[job.workflow_job_id] = job
        await self._persist_run(job, last_event=None)
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

    async def cancel(self, workflow_job_id: str) -> bool:
        job = self.get(workflow_job_id)
        if job is None:
            return False
        if job.status in {"completed", "failed", "canceled"}:
            return False

        job.cancel_requested = True
        canceled_runner_jobs: list[str] = []
        for runner_job_id in list(job.runner_job_ids):
            try:
                result = await self.runner.cancel_job(runner_job_id)
                if result.get("canceled"):
                    canceled_runner_jobs.append(runner_job_id)
            except Exception:
                continue

        job.status = "canceled"
        job.ended_at = utc_now()
        await self._emit(
            job,
            {
                "type": "meta",
                "event": "canceled",
                "status": job.status,
                "canceled_runner_jobs": canceled_runner_jobs,
                "ended_at": job.ended_at,
            },
        )
        return True

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
            preflight_payload = await self.runner.preflight(job.cwd_relative, timeout_sec=8.0)
            await self._emit(
                job,
                {
                    "type": "meta",
                    "event": "preflight_ok",
                    "status": job.status,
                    "runner_health": preflight_payload.get("health"),
                },
            )
            self._raise_if_canceled(job)
            plan_output = ""
            implement_output = ""
            review_output = ""
            verdict: str | None = None

            for step in job.pipeline_steps:
                self._raise_if_canceled(job)
                if step == "plan":
                    plan_prompt = self._build_plan_prompt(job.user_message)
                    plan_result = await self._run_agent_step(
                        job,
                        "plan",
                        "gemini",
                        plan_prompt,
                        command_template=job.gemini_cmd_template or None,
                    )
                    plan_output = plan_result.output
                    self._save_artifact(job, "plan", self._extract_section(plan_output, "Plan"))
                    self._save_artifact(job, "tasks", self._extract_section(plan_output, "Tasks"))
                    continue

                if step == "implement":
                    impl_prompt = self._build_implement_prompt(job.user_message, plan_output)
                    impl_result = await self._run_agent_step(
                        job,
                        "implement",
                        "codex",
                        impl_prompt,
                        command_template=job.codex_cmd_template or None,
                    )
                    implement_output = impl_result.output
                    self._save_artifact(job, "patch", self._extract_section(implement_output, "Patch"))
                    self._save_artifact(job, "files", self._extract_section(implement_output, "Files"))
                    continue

                if step == "review":
                    review_prompt = self._build_review_prompt(job.user_message, plan_output, implement_output)
                    review_result = await self._run_agent_step(
                        job,
                        "review",
                        "gemini",
                        review_prompt,
                        command_template=job.gemini_cmd_template or None,
                    )
                    review_output = review_result.output
                    review_section = self._extract_section(review_output, "Review")
                    if not review_section.strip():
                        review_section = review_output
                    self._save_artifact(job, "review", review_section)
                    verdict = self._parse_verdict(review_output)
                    await self._emit(
                        job,
                        {"type": "meta", "event": "review_verdict", "verdict": verdict},
                    )
                    continue

                if step == "fix":
                    if not job.enable_fix:
                        await self._emit(
                            job,
                            {"type": "step", "event": "skipped", "step": "fix", "reason": "fix_disabled"},
                        )
                        continue
                    if verdict is None:
                        await self._emit(
                            job,
                            {"type": "step", "event": "skipped", "step": "fix", "reason": "no_review_verdict"},
                        )
                        continue
                    if verdict != "FAIL":
                        await self._emit(
                            job,
                            {"type": "step", "event": "skipped", "step": "fix", "reason": "review_pass"},
                        )
                        continue
                    fix_prompt = self._build_fix_prompt(job.user_message, implement_output, review_output)
                    fix_result = await self._run_agent_step(
                        job,
                        "fix",
                        "codex",
                        fix_prompt,
                        command_template=job.codex_cmd_template or None,
                    )
                    implement_output = fix_result.output
                    self._save_artifact(job, "patch", self._extract_section(implement_output, "Patch"))
                    self._save_artifact(job, "files", self._extract_section(implement_output, "Files"))

            self._raise_if_canceled(job)

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
        except WorkflowCanceled as exc:
            if job.status != "canceled":
                job.status = "canceled"
                job.ended_at = utc_now()
                await self._emit(
                    job,
                    {
                        "type": "meta",
                        "event": "canceled",
                        "status": job.status,
                        "message": str(exc),
                        "ended_at": job.ended_at,
                    },
                )
        except Exception as exc:  # pragma: no cover - runtime guard
            if job.status == "canceled":
                return
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

    async def _run_agent_step(
        self,
        job: WorkflowJob,
        step: str,
        runner: str,
        prompt: str,
        command_template: str | None = None,
    ) -> StepResult:
        self._raise_if_canceled(job)
        await self._emit(
            job,
            {"type": "step", "event": "start", "step": step, "runner": runner},
        )
        runner_job_id = await self.runner.start_job(
            runner,
            job.session_id,
            prompt,
            job.cwd_relative,
            command_template=command_template,
        )
        job.runner_job_ids.append(runner_job_id)
        await self._emit(
            job,
            {
                "type": "step",
                "event": "runner_job_created",
                "step": step,
                "runner": runner,
                "runner_job_id": runner_job_id,
                "command_template": command_template or "",
            },
        )

        try:
            output_lines: list[str] = []
            async for event in self.runner.stream_job(runner_job_id):
                if job.cancel_requested:
                    await self.runner.cancel_job(runner_job_id)
                    raise WorkflowCanceled("workflow canceled by user")
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
        finally:
            if runner_job_id in job.runner_job_ids:
                job.runner_job_ids.remove(runner_job_id)

    async def _emit(self, job: WorkflowJob, event: dict[str, Any]) -> None:
        async with job.condition:
            job.seq += 1
            payload = {"seq": job.seq, "timestamp": utc_now(), **event}
            job.events.append(payload)
            job.condition.notify_all()
        await self.journal.append(job.session_id, {"workflow_job_id": job.workflow_job_id, **payload})
        await self.conversation_store.append(
            job.project_id,
            {
                "source": "workflow_event",
                "project_id": job.project_id,
                "session_id": job.session_id,
                "workflow_job_id": job.workflow_job_id,
                **payload,
            },
        )
        await self._persist_run(job, last_event=payload)

    def _save_artifact(self, job: WorkflowJob, name: str, content: str) -> None:
        if content.strip():
            job.artifacts[name] = content

    async def _persist_run(self, job: WorkflowJob, last_event: dict[str, Any] | None) -> None:
        payload = {
            "workflow_job_id": job.workflow_job_id,
            "project_id": job.project_id,
            "session_id": job.session_id,
            "status": job.status,
            "cwd_relative": job.cwd_relative,
            "enable_fix": job.enable_fix,
            "pipeline_steps": job.pipeline_steps,
            "codex_cmd_template": job.codex_cmd_template,
            "gemini_cmd_template": job.gemini_cmd_template,
            "cancel_requested": job.cancel_requested,
            "started_at": job.started_at,
            "ended_at": job.ended_at,
            "updated_at": utc_now(),
            "artifacts": job.artifacts,
            "last_event": last_event,
        }
        await self.run_store.upsert(job.project_id, job.workflow_job_id, payload)

    @staticmethod
    def _raise_if_canceled(job: WorkflowJob) -> None:
        if job.cancel_requested or job.status == "canceled":
            raise WorkflowCanceled("workflow canceled by user")

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
