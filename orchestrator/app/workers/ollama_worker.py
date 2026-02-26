from __future__ import annotations

import time

import requests

from app.config import (
    BAD_REQUEST_RETRY_COUNT,
    BAD_REQUEST_RETRY_DELAY_SECONDS,
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
)
from app.models.schemas import WorkerTaskInput
from app.utils.retry import retry_delay_seconds
from app.workers.base import BaseWorker


class OllamaWorker(BaseWorker):
    name = "ollama"
    output_subdir = "artifacts"

    def _run(self, task: WorkerTaskInput) -> dict[str, str]:
        payload = {
            "model": task.model or OLLAMA_MODEL,
            "prompt": task.prompt,
            "stream": False,
        }

        max_attempts = BAD_REQUEST_RETRY_COUNT + 1
        response = None
        retry_logs: list[str] = []
        for attempt in range(1, max_attempts + 1):
            response = requests.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json=payload,
                timeout=90,
            )
            if response.status_code != 400 or attempt >= max_attempts:
                break
            wait_sec = retry_delay_seconds(BAD_REQUEST_RETRY_DELAY_SECONDS, attempt)
            retry_logs.append(f"attempt {attempt}: 400 bad request -> retry after {wait_sec:.1f}s")
            time.sleep(wait_sec)

        if response is None:
            raise RuntimeError("Ollama request did not execute")
        if response.status_code == 400:
            detail = response.text[:500]
            raise RuntimeError(f"Ollama API returned 400 Bad Request after retries: {detail}")

        response.raise_for_status()
        data = response.json()

        text = data.get("response", "")
        markdown = (
            "# Ollama Output\n\n"
            f"- model: `{payload['model']}`\n"
            f"- endpoint: `{OLLAMA_BASE_URL}/api/generate`\n\n"
            f"- attempts: `{len(retry_logs) + 1}`\n"
            f"- bad_request_retries: `{len(retry_logs)}`\n\n"
            "## Retry Logs\n\n"
            f"```\n{chr(10).join(retry_logs) if retry_logs else '(none)'}\n```\n\n"
            "## Prompt\n\n"
            f"```\n{task.prompt}\n```\n\n"
            "## Response\n\n"
            f"{text}\n"
        )

        return {
            "stdout": text,
            "stderr": "",
            "markdown": markdown,
        }
