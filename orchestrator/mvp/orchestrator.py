from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import shlex
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

TASK_NAME_TO_DEFAULT_AGENT = {
    "task_a": "gemini",
    "task_b": "codex",
}


@dataclass
class TaskItem:
    name: str
    agent_type: str
    instruction: str
    rag_query: str
    cwd: str
    cli_args: list[str]
    depends_on: list[str]


def utc_now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def normalize_task_name(name: str) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", name.lower()).strip("_")


def parse_spec(file_path: str) -> dict[str, Any]:
    path = Path(file_path)
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"design spec file not found: {file_path}")

    raw = json.loads(path.read_text(encoding="utf-8"))
    tasks: list[TaskItem] = []

    def build_task(raw_task: Any, fallback_name: str) -> TaskItem:
        if isinstance(raw_task, str):
            instruction = raw_task.strip()
            source: dict[str, Any] = {}
        elif isinstance(raw_task, dict):
            instruction = str(
                raw_task.get("instruction")
                or raw_task.get("task")
                or raw_task.get("prompt")
                or raw_task.get("description")
                or ""
            ).strip()
            source = raw_task
        else:
            raise ValueError(f"{fallback_name} must be object/string")

        if not instruction:
            raise ValueError(f"{fallback_name} instruction is empty")

        key = normalize_task_name(fallback_name)
        agent_type = str(source.get("agent_type") or source.get("agent") or "").strip().lower()
        if not agent_type:
            agent_type = TASK_NAME_TO_DEFAULT_AGENT.get(key, "gemini")
        if agent_type not in {"gemini", "codex"}:
            raise ValueError(f"unsupported agent_type for {fallback_name}: {agent_type}")

        rag_query = str(source.get("rag_query") or source.get("query") or instruction).strip()
        cwd = str(source.get("cwd") or ".").strip() or "."
        cli_args_raw = source.get("cli_args") or []
        if isinstance(cli_args_raw, str):
            cli_args = shlex.split(cli_args_raw)
        elif isinstance(cli_args_raw, list):
            cli_args = [str(item) for item in cli_args_raw]
        else:
            raise ValueError(f"{fallback_name}.cli_args must be list/string")

        depends_raw = source.get("depends_on") or []
        if isinstance(depends_raw, str):
            depends_on = [depends_raw.strip()] if depends_raw.strip() else []
        elif isinstance(depends_raw, list):
            depends_on = [str(item).strip() for item in depends_raw if str(item).strip()]
        else:
            raise ValueError(f"{fallback_name}.depends_on must be list/string")

        return TaskItem(
            name=fallback_name,
            agent_type=agent_type,
            instruction=instruction,
            rag_query=rag_query,
            cwd=cwd,
            cli_args=cli_args,
            depends_on=depends_on,
        )

    if isinstance(raw.get("tasks"), list):
        for idx, row in enumerate(raw["tasks"], start=1):
            row_obj = row if isinstance(row, dict) else {"instruction": str(row)}
            name = str(row_obj.get("name") or f"task_{idx}")
            tasks.append(build_task(row_obj, name))
    else:
        task_a = raw.get("Task_A") or raw.get("task_a")
        task_b = raw.get("Task_B") or raw.get("task_b")
        if task_a is None and task_b is None:
            raise ValueError("spec must contain tasks list or Task_A/Task_B")
        if task_a is not None:
            tasks.append(build_task(task_a, "Task_A"))
        if task_b is not None:
            tasks.append(build_task(task_b, "Task_B"))

    return {
        "source_file": str(path),
        "project": raw.get("project") or raw.get("project_id"),
        "tasks": tasks,
    }


def get_rag_context(
    query: str,
    rag_root: str,
    max_docs: int = 3,
    max_chars: int = 2200,
    max_scan_files: int | None = None,
) -> str:
    """
    Dummy RAG interface.
    현재는 로컬 파일 기반 키워드 검색이며, 추후 벡터 DB로 교체 가능한 인터페이스다.
    """
    root = Path(rag_root)
    if not root.exists() or not root.is_dir():
        return "(RAG) context root not found."

    tokens = [tok.lower() for tok in re.findall(r"\w+", query or "") if len(tok) >= 2]
    if not tokens:
        return "(RAG) no query tokens."

    allowed_ext = {".md", ".txt", ".py", ".json", ".yaml", ".yml"}
    skip_dirs = {
        ".git",
        ".venv",
        ".codex",
        ".auth",
        "node_modules",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
    }
    scan_limit = max_scan_files or int(os.getenv("RAG_MAX_SCAN_FILES", "400"))

    scored: list[tuple[float, Path, str]] = []
    scanned = 0
    reached_limit = False

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in skip_dirs and not d.startswith(".")]
        for filename in filenames:
            if filename.startswith("."):
                continue
            path = Path(dirpath) / filename
            if path.suffix.lower() not in allowed_ext:
                continue
            if path.stat().st_size > 800_000:
                continue
            scanned += 1
            if scanned > scan_limit:
                reached_limit = True
                break
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            if not text.strip():
                continue

            text_lower = text.lower()
            score = 0.0
            for tok in tokens:
                cnt = text_lower.count(tok)
                if cnt:
                    score += 1.0 + min(4.0, cnt * 0.25)
            if score > 0:
                scored.append((score, path, text))
        if reached_limit:
            break

    if not scored:
        return "(RAG) no relevant local context found."

    scored.sort(key=lambda row: row[0], reverse=True)
    picked = scored[:max_docs]
    parts: list[str] = []
    remain = max_chars
    for idx, (score, path, text) in enumerate(picked, start=1):
        snippet = " ".join(text.replace("\r", " ").replace("\n", " ").split())
        snippet = snippet[:420] + ("..." if len(snippet) > 420 else "")
        block = f"[{idx}] score={score:.2f} file={path}\n{snippet}"
        if len(block) > remain:
            block = block[: max(0, remain - 3)] + "..."
        parts.append(block)
        remain -= len(block) + 2
        if remain <= 0:
            break

    return "\n\n".join(parts)


def build_cli_command(agent_type: str, prompt: str, extra_args: list[str]) -> list[str]:
    env_key = "GEMINI_CLI_CMD" if agent_type == "gemini" else "CODEX_CLI_CMD"
    default_cmd = (
        "gemini --prompt {prompt} --yolo"
        if agent_type == "gemini"
        else "codex exec --skip-git-repo-check --full-auto {prompt}"
    )
    template = os.getenv(env_key, default_cmd).strip() or default_cmd
    base = shlex.split(template)

    resolved: list[str] = []
    used_placeholder = False
    for token in base:
        if "{prompt}" in token:
            used_placeholder = True
            resolved.append(token.replace("{prompt}", prompt))
        else:
            resolved.append(token)
    if not used_placeholder:
        resolved.append(prompt)
    resolved.extend(extra_args)
    return resolved


def build_agent_env(agent_type: str) -> dict[str, str]:
    env = os.environ.copy()
    # Runtime API-key injection is intentionally disabled.
    # Use mounted CLI login/session files inside Docker instead.
    for blocked in ("OPENAI_API_KEY", "GEMINI_API_KEY", "GEMINI_SESSION_COOKIE", "GITHUB_TOKEN", "GH_TOKEN"):
        env.pop(blocked, None)
    return env


async def dispatch_to_cli(
    agent_type: str,
    task: TaskItem,
    context: str,
    workspace_dir: str,
    timeout_sec: int = 900,
    dry_run: bool = False,
) -> dict[str, Any]:
    if agent_type not in {"gemini", "codex"}:
        raise ValueError(f"unsupported agent_type: {agent_type}")

    composed_prompt = (
        "You are a CLI coding agent running inside docker orchestrator.\n"
        "Follow task instruction exactly and use RAG context only when relevant.\n\n"
        "## Task Instruction\n"
        f"{task.instruction}\n\n"
        "## Retrieved Context (RAG)\n"
        f"{context}\n"
    )
    cmd = build_cli_command(agent_type, composed_prompt, task.cli_args)
    run_cwd = str((Path(workspace_dir) / task.cwd).resolve())

    result = {
        "task_name": task.name,
        "agent_type": agent_type,
        "command": cmd,
        "cwd": run_cwd,
        "started_at": utc_now_iso(),
        "dry_run": dry_run,
    }

    if not Path(run_cwd).exists():
        result.update(
            {
                "status": "failed",
                "return_code": 2,
                "stdout": "",
                "stderr": f"working directory not found: {run_cwd}",
                "ended_at": utc_now_iso(),
            }
        )
        return result

    cli_binary = cmd[0] if cmd else ""
    if not cli_binary or shutil.which(cli_binary) is None:
        result.update(
            {
                "status": "failed",
                "return_code": 127,
                "stdout": "",
                "stderr": (
                    f"required CLI is not installed or not in PATH: {cli_binary}. "
                    "Install CLI in Docker image or check CLI command template."
                ),
                "ended_at": utc_now_iso(),
            }
        )
        return result

    if dry_run:
        result.update(
            {
                "status": "dry_run",
                "return_code": 0,
                "stdout": "",
                "stderr": "",
                "ended_at": utc_now_iso(),
            }
        )
        return result

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=run_cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=build_agent_env(agent_type),
        )
    except FileNotFoundError as exc:
        result.update(
            {
                "status": "failed",
                "return_code": 127,
                "stdout": "",
                "stderr": f"CLI binary not found: {exc}",
                "ended_at": utc_now_iso(),
            }
        )
        return result

    try:
        out_b, err_b = await asyncio.wait_for(proc.communicate(), timeout=timeout_sec)
        stdout = out_b.decode("utf-8", errors="replace")
        stderr = err_b.decode("utf-8", errors="replace")
        code = int(proc.returncode or 0)
        status = "success" if code == 0 else "failed"
        result.update(
            {
                "status": status,
                "return_code": code,
                "stdout": stdout,
                "stderr": stderr,
                "ended_at": utc_now_iso(),
            }
        )
        return result
    except asyncio.TimeoutError:
        proc.kill()
        out_b, err_b = await proc.communicate()
        result.update(
            {
                "status": "failed",
                "return_code": 124,
                "stdout": out_b.decode("utf-8", errors="replace"),
                "stderr": f"timeout after {timeout_sec}s\n{err_b.decode('utf-8', errors='replace')}",
                "ended_at": utc_now_iso(),
            }
        )
        return result


def save_run_log(output_dir: str, payload: dict[str, Any]) -> str:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = out / f"run_{stamp}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return str(path)


async def run_orchestrator(
    *,
    spec_path: str,
    workspace_dir: str,
    rag_dir: str,
    output_dir: str,
    timeout_sec: int,
    parallel: bool,
    dry_run: bool,
) -> dict[str, Any]:
    parsed = parse_spec(spec_path)
    tasks: list[TaskItem] = parsed["tasks"]
    normalized_task_names = {normalize_task_name(task.name) for task in tasks}
    independent_tasks = all(not task.depends_on for task in tasks)
    auto_parallel = len(tasks) > 1 and independent_tasks
    run_parallel = len(tasks) > 1 and independent_tasks and (parallel or auto_parallel)

    async def run_one(task: TaskItem) -> dict[str, Any]:
        try:
            context = get_rag_context(task.rag_query, rag_dir)
            return await dispatch_to_cli(
                task.agent_type,
                task=task,
                context=context,
                workspace_dir=workspace_dir,
                timeout_sec=timeout_sec,
                dry_run=dry_run,
            )
        except Exception as exc:  # noqa: BLE001
            return {
                "task_name": task.name,
                "agent_type": task.agent_type,
                "status": "failed",
                "return_code": 1,
                "stdout": "",
                "stderr": f"task execution error: {exc}",
                "started_at": utc_now_iso(),
                "ended_at": utc_now_iso(),
            }

    started_at = utc_now_iso()
    if run_parallel:
        results = await asyncio.gather(*(run_one(task) for task in tasks))
    else:
        results = []
        status_map: dict[str, str] = {}
        for task in tasks:
            normalized_name = normalize_task_name(task.name)
            deps = [normalize_task_name(dep) for dep in task.depends_on]
            unknown_deps = [dep for dep in deps if dep and dep not in normalized_task_names]
            unmet_deps = [dep for dep in deps if dep and status_map.get(dep) not in {"success", "dry_run"}]
            if unknown_deps:
                results.append(
                    {
                        "task_name": task.name,
                        "agent_type": task.agent_type,
                        "status": "failed",
                        "return_code": 2,
                        "stdout": "",
                        "stderr": f"unknown dependency task(s): {', '.join(unknown_deps)}",
                        "started_at": utc_now_iso(),
                        "ended_at": utc_now_iso(),
                    }
                )
                status_map[normalized_name] = "failed"
                continue
            if unmet_deps:
                results.append(
                    {
                        "task_name": task.name,
                        "agent_type": task.agent_type,
                        "status": "skipped",
                        "return_code": 3,
                        "stdout": "",
                        "stderr": (
                            "dependency task(s) not successful: "
                            + ", ".join(unmet_deps)
                        ),
                        "started_at": utc_now_iso(),
                        "ended_at": utc_now_iso(),
                    }
                )
                status_map[normalized_name] = "skipped"
                continue
            results.append(await run_one(task))
            status_map[normalized_name] = str(results[-1].get("status", "failed"))

    failed = [row for row in results if row.get("status") not in {"success", "dry_run"}]
    payload = {
        "started_at": started_at,
        "ended_at": utc_now_iso(),
        "spec_path": spec_path,
        "workspace_dir": workspace_dir,
        "rag_dir": rag_dir,
        "parallel_requested": parallel,
        "parallel_executed": run_parallel,
        "auto_parallel": auto_parallel,
        "dry_run": dry_run,
        "task_count": len(tasks),
        "failed_count": len(failed),
        "results": results,
    }
    payload["log_path"] = save_run_log(output_dir, payload)
    return payload


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Multi-agent CLI orchestrator MVP")
    parser.add_argument("--spec", default=os.getenv("SPEC_PATH", "/workspace/design_spec.json"))
    parser.add_argument("--workspace-dir", default=os.getenv("WORKSPACE_DIR", "/workspace"))
    parser.add_argument("--rag-dir", default=os.getenv("RAG_DIR", "/workspace"))
    parser.add_argument("--output-dir", default=os.getenv("MVP_OUTPUT_DIR", "/app/data/mvp_runs"))
    parser.add_argument("--timeout-sec", type=int, default=int(os.getenv("CLI_TIMEOUT_SEC", "900")))
    parser.add_argument("--parallel", action="store_true", help="Task_A/B 병렬 실행")
    parser.add_argument("--dry-run", action="store_true", help="CLI를 실행하지 않고 명령 계획만 출력")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        result = asyncio.run(
            run_orchestrator(
                spec_path=args.spec,
                workspace_dir=args.workspace_dir,
                rag_dir=args.rag_dir,
                output_dir=args.output_dir,
                timeout_sec=args.timeout_sec,
                parallel=args.parallel,
                dry_run=args.dry_run,
            )
        )
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"status": "failed", "error": str(exc)}, ensure_ascii=False))
        return 1

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("failed_count", 0) == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
