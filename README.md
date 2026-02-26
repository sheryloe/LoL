# LoL Co-Worker Chat Workspace

This repository runs a **co-worker chat tool** where one project room maps to one collaboration context.

- Orchestrator (Docker): workflow control + web UI + room state
- Runner (Docker): codex/gemini/git subprocess execution
- Data-first traceability: conversation, runs, journals are persisted per project

## Current Mode

- Active source of truth: `D:\AI_Vibe\LoL`
- Branch: `main`
- Remote: `https://github.com/sheryloe/LoL.git`

## Architecture

1. User sends a chat request to Orchestrator (`POST /api/chat`)
2. Orchestrator resolves project defaults (session, cwd, fix-mode)
3. Workflow pipeline runs (`plan -> implement -> review -> fix(optional)`)
4. Runner executes codex/gemini (or mock agent) and streams events
5. Orchestrator persists conversation and run states by project room

## Runtime Modes

1. Real mode (default): runner requires real `codex`/`gemini` CLI + auth.
2. Auto mode: real-first mode (no mock fallback). If requirements are missing, workflow start is blocked by preflight.
3. Mock mode: debug-only mode, must be explicitly enabled (`RUNNER_AGENT_MODE=mock`).

## 10-Step Structured Build

Detailed docs:
- [Step Index 1-10](./docs/steps/README.md)
- [Roadmap](./ROADMAP_CHAT_PROJECT.md)
- [Blog Structure](./docs/blog/README.md)
- [Strict Real Execution Plan](./docs/STRICT_REAL_EXECUTION_PLAN.md)

## Backtest / Smoke Evidence

Latest run:
- [Step10 Smoke Report](./docs/BACKTEST_REPORT_2026-02-26_STEP10.md)
- [Step10 Raw JSON](./docs/backtest_results_2026-02-26_step10.json)
- [Docker Stack 5-Step Report](./docs/BACKTEST_REPORT_2026-02-26_DOCKER_STACK.md)
- [Docker Stack 5-Step Raw JSON](./docs/backtest_results_2026-02-26_docker_stack.json)
- [Docker CLI Mode 5-Step Report](./docs/BACKTEST_REPORT_2026-02-26_DOCKER_CLI_MODE.md)
- [Docker CLI Mode 5-Step Raw JSON](./docs/backtest_results_2026-02-26_docker_cli_mode.json)
- [Strict Preflight Report](./docs/BACKTEST_REPORT_2026-02-26_STRICT_PREFLIGHT.md)
- [Strict Preflight Raw JSON](./docs/backtest_results_2026-02-26_strict_preflight.json)

## TODO (Visible on GitHub README)

### P0

1. Add automated regression tests for preflight fail-fast and workflow cancel invariants.
2. Add clearer runtime diagnostics in UI for CLI/auth misconfiguration.
3. Add step-pipeline UI editor (`plan/implement/review/fix`) instead of API-only control.

### P1

1. Per-project step pipeline toggle/order (`plan/implement/review/fix` on/off) in UI.
2. Per-project CLI argument templates and override policy.
3. Artifact timeline UX improvement (step status, artifacts, run summary in one thread view).
4. Run-to-run file diff viewer.
5. Guarded git flow in UI (`status -> draft -> commit -> push`).

### P2

1. Permission tiers (`read_only`, `write_limited`, `full_write`).
2. Replace static token style with stronger auth + secret loading.
3. Audit trail model and API/UI.
4. Test pyramid expansion (unit/integration/e2e/failure path).
5. Observability (trace_id, metrics, structured logs, dashboard hooks).

## Run

### 1) Docker Stack (Orchestrator + Runner)

```powershell
cd D:\AI_Vibe\LoL\orchestrator
docker compose up --build
```

### 2) Open

- `http://localhost:8080`

### 3) Real CLI/Auth (Optional)

Create `D:\AI_Vibe\LoL\orchestrator\.env` from `.env.example` and set:

- `RUNNER_AGENT_MODE=real`
- `CODEX_CMD`
- `GEMINI_CMD`
- `OPENAI_API_KEY`
- `GEMINI_API_KEY`

Recommended command templates:

- `CODEX_CMD=codex exec --skip-git-repo-check --full-auto {prompt}`
- `GEMINI_CMD=gemini --prompt {prompt} --yolo`

Optional interactive auth inside Docker:

```powershell
docker exec -it lol-runner codex login
```

Runtime verification:

```powershell
curl http://localhost:8765/health
```

Strict readiness verification:

```powershell
curl "http://localhost:8765/preflight/agents?cwd_relative=."
```

Check fields:

- `agent_mode`
- `codex_source`
- `gemini_source`
- `openai_api_key_present`
- `gemini_api_key_present`
