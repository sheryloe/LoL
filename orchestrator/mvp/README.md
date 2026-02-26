# MVP Orchestrator

Python-based multi-agent orchestrator that reads design spec tasks, attaches local RAG context, and dispatches Gemini/Codex CLIs inside Docker.

Core functions:

1. `parse_spec(file_path)`
2. `get_rag_context(query)`
3. `dispatch_to_cli(agent_type, task, context)`
4. `run_orchestrator()`

Highlights:

- `Task_A` / `Task_B` or `tasks[]` JSON supported
- Shell injection-safe command invocation via list args
- Independent tasks run in parallel using `asyncio.gather`
- Dependency-aware fallback to sequential execution (`depends_on`)
- Clear error when CLI binary is missing
- Session-auth mount friendly (`/root/.config/gh`, `/root/.codex`, `/root/.config/gemini`)
- Runtime API-key injection disabled (CLI login/session mount only)

Run inside Docker:

```bash
docker compose run --rm orchestrator \
  python /app/mvp/orchestrator.py \
  --spec /workspace/orchestrator/mvp/design_spec.example.json \
  --workspace-dir /workspace \
  --rag-dir /workspace \
  --dry-run
```

Parallel run:

```bash
docker compose run --rm orchestrator \
  python /app/mvp/orchestrator.py \
  --spec /workspace/orchestrator/mvp/design_spec.example.json \
  --workspace-dir /workspace \
  --rag-dir /workspace \
  --parallel \
  --dry-run
```
