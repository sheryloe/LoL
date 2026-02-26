from __future__ import annotations

import shlex
import subprocess
import time

from app.config import (
    BAD_REQUEST_RETRY_COUNT,
    BAD_REQUEST_RETRY_DELAY_SECONDS,
    GEMINI_CLI_BIN,
    GEMINI_CLI_CMD,
    SUBPROCESS_TIMEOUT_SECONDS,
)
from app.models.schemas import WorkerTaskInput
from app.utils.retry import looks_like_bad_request, retry_delay_seconds
from app.workers.base import BaseWorker
from app.workers.cli_command import build_cli_command


class GeminiWorker(BaseWorker):
    name = "gemini"
    output_subdir = "gemini_outputs"

    def _run(self, task: WorkerTaskInput) -> dict[str, str]:
        def decode_output(raw: bytes) -> str:
            for enc in ("utf-8", "cp949"):
                try:
                    return raw.decode(enc)
                except UnicodeDecodeError:
                    continue
            return raw.decode("utf-8", errors="replace")

        cmd, use_stdin_prompt = build_cli_command(
            cli_bin=GEMINI_CLI_BIN,
            prompt=task.prompt,
            cli_args=task.cli_args,
            default_template=GEMINI_CLI_CMD,
        )
        max_attempts = BAD_REQUEST_RETRY_COUNT + 1
        retry_logs: list[str] = []
        completed = None
        stdout_text = ""
        stderr_text = ""
        for attempt in range(1, max_attempts + 1):
            try:
                kwargs = {
                    "args": cmd,
                    "capture_output": True,
                    "timeout": SUBPROCESS_TIMEOUT_SECONDS,
                    "check": False,
                }
                if use_stdin_prompt:
                    kwargs["input"] = task.prompt.encode("utf-8")
                completed = subprocess.run(**kwargs)
            except FileNotFoundError as exc:
                raise RuntimeError(f"Gemini CLI not found: {GEMINI_CLI_BIN}") from exc

            stdout_text = decode_output(completed.stdout or b"")
            stderr_text = decode_output(completed.stderr or b"")
            if attempt >= max_attempts:
                break
            if not looks_like_bad_request(completed.returncode, stdout_text, stderr_text):
                break
            wait_sec = retry_delay_seconds(BAD_REQUEST_RETRY_DELAY_SECONDS, attempt)
            retry_logs.append(f"attempt {attempt}: bad request detected -> retry after {wait_sec:.1f}s")
            time.sleep(wait_sec)

        if completed is None:
            raise RuntimeError("Gemini execution failed before process start")

        command_text = shlex.join(cmd)
        markdown = (
            "# Gemini Output\n\n"
            f"- command: `{command_text}`\n"
            f"- return_code: `{completed.returncode}`\n\n"
            f"- attempts: `{len(retry_logs) + 1}`\n"
            f"- bad_request_retries: `{len(retry_logs)}`\n\n"
            "## Retry Logs\n\n"
            f"```\n{chr(10).join(retry_logs) if retry_logs else '(none)'}\n```\n\n"
            "## Prompt\n\n"
            f"```\n{task.prompt}\n```\n\n"
            "## STDOUT\n\n"
            f"```\n{stdout_text}\n```\n\n"
            "## STDERR\n\n"
            f"```\n{stderr_text}\n```\n"
        )

        return {
            "stdout": stdout_text,
            "stderr": stderr_text,
            "markdown": markdown,
        }
