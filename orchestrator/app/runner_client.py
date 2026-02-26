from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from typing import Any

import httpx


class RunnerClient:
    def __init__(self, base_url: str, timeout_sec: float = 600.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout_sec

    async def start_job(self, runner: str, session_id: str, prompt: str, cwd_relative: str) -> str:
        endpoint = f"{self.base_url}/run/{runner}"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                endpoint,
                json={
                    "session_id": session_id,
                    "prompt": prompt,
                    "cwd_relative": cwd_relative,
                },
            )
            response.raise_for_status()
            payload = response.json()
            return payload["job_id"]

    async def get_job(self, job_id: str) -> dict[str, Any]:
        endpoint = f"{self.base_url}/jobs/{job_id}"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(endpoint)
            response.raise_for_status()
            return response.json()

    async def git_status(self, cwd_relative: str) -> dict[str, Any]:
        endpoint = f"{self.base_url}/git/status"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(endpoint, params={"cwd_relative": cwd_relative})
            response.raise_for_status()
            return response.json()

    async def stream_job(self, job_id: str) -> AsyncGenerator[dict[str, Any], None]:
        endpoint = f"{self.base_url}/stream/{job_id}"
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream("GET", endpoint) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    raw = line.removeprefix("data: ").strip()
                    if not raw:
                        continue
                    try:
                        yield json.loads(raw)
                    except json.JSONDecodeError:
                        continue

