from __future__ import annotations

from typing import Any

from app.models.schemas import CoworkRunRequest, WorkerRunRequest, WorkerTaskInput
from app.services.chat_service import chat_service
from app.services.project_service import project_service
from app.services.worker_service import worker_service


def _normalize_text(raw: str) -> str:
    text = (raw or "").strip()
    if text:
        return text
    return "(no output)"


class CoworkService:
    def _order(self, order: str) -> list[str]:
        if order == "gemini_then_codex":
            return ["gemini", "codex"]
        return ["codex", "gemini"]

    def _build_context(self, session: dict[str, Any], limit: int = 6) -> str:
        lines: list[str] = []
        for msg in (session.get("messages") or [])[-limit:]:
            role = str(msg.get("role", "unknown"))
            worker = str(msg.get("worker", "")).strip()
            prefix = f"{role}:{worker}" if worker else role
            content = str(msg.get("content", "")).strip()
            if not content:
                continue
            lines.append(f"[{prefix}] {content}")
        return "\n".join(lines) if lines else "(empty)"

    def _worker_prompt(self, worker: str, user_prompt: str, session: dict[str, Any]) -> str:
        thread = self._build_context(session)
        return (
            f"You are {worker} in a co-worker coding room.\n"
            "Collaborate with the other agent and move the implementation forward.\n"
            "Be concrete: what to change, why, and next handoff.\n\n"
            "## User Request\n"
            f"{user_prompt}\n\n"
            "## Current Thread\n"
            f"{thread}\n"
        )

    def run(self, project_id: str, request: CoworkRunRequest) -> dict[str, Any]:
        project_service.get_project(project_id)
        session = chat_service.get_or_create_session(project_id=project_id, session_id=request.session_id)

        chat_service.append_message(
            session,
            role="user",
            content=request.prompt,
            metadata={
                "mode": "co-work",
                "rounds": request.rounds,
                "order": request.order,
            },
        )

        worker_order = self._order(request.order)
        step_results: list[dict[str, Any]] = []

        for round_no in range(1, request.rounds + 1):
            for worker_name in worker_order:
                prompt = self._worker_prompt(worker_name, request.prompt, session)
                cli_args = request.codex_cli_args if worker_name == "codex" else request.gemini_cli_args

                result = worker_service.run_worker(
                    project_id=project_id,
                    worker_name=worker_name,
                    request=WorkerRunRequest(
                        task=WorkerTaskInput(prompt=prompt, cli_args=cli_args),
                        write_enabled=request.write_enabled,
                    ),
                )

                content = _normalize_text(result.stdout or result.stderr)
                chat_service.append_message(
                    session,
                    role="assistant",
                    content=content,
                    worker=worker_name,
                    metadata={
                        "round": round_no,
                        "output_path": result.output_path,
                        "metadata_path": result.metadata_path,
                        "success": result.success,
                    },
                )
                step_results.append(
                    {
                        "round": round_no,
                        "worker": worker_name,
                        "success": result.success,
                        "output_path": result.output_path,
                        "metadata_path": result.metadata_path,
                    }
                )

        chat_service.save_session(project_id=project_id, session=session, write_enabled=request.write_enabled)
        return {
            "project_id": project_id,
            "session_id": session.get("session_id"),
            "rounds": request.rounds,
            "worker_order": worker_order,
            "turn_count": len(session.get("messages") or []),
            "steps": step_results,
        }


cowork_service = CoworkService()
