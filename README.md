# LoL Co-Worker Chat Workspace

This repository runs a **co-worker chat tool** where one project room maps to one collaboration context.

- Orchestrator (Docker): workflow control + web UI + room state
- Runner (Host Windows): codex/gemini/git subprocess execution
- Data-first traceability: conversation, runs, journals are persisted per project

## Current Mode

- Active source of truth: `D:\AI_Vibe\LoL`
- Branch: `main`
- Remote: `https://github.com/sheryloe/LoL.git`

## Architecture

1. User sends a chat request to Orchestrator (`POST /api/chat`)
2. Orchestrator resolves project defaults (session, cwd, fix-mode)
3. Workflow pipeline runs (`plan -> implement -> review -> fix(optional)`)
4. Runner executes codex/gemini on host and streams events
5. Orchestrator persists conversation and run states by project room

## 10-Step Structured Build

Detailed docs:
- [Step Index 1-10](./docs/steps/README.md)
- [Roadmap](./ROADMAP_CHAT_PROJECT.md)
- [Blog Structure](./docs/blog/README.md)

## Backtest / Smoke Evidence

Latest run:
- [Step10 Smoke Report](./docs/BACKTEST_REPORT_2026-02-26_STEP10.md)
- [Step10 Raw JSON](./docs/backtest_results_2026-02-26_step10.json)

## TODO (Visible on GitHub README)

### P0

1. Fix host-to-container runner routing stability (`host.docker.internal`) across Docker Desktop and Rancher Desktop.
2. Add automated regression tests for preflight fail-fast and workflow cancel invariants.
3. Add clearer runtime diagnostics in UI when runner is reachable locally but unreachable from orchestrator container.

### P1

1. Per-project step pipeline toggle/order (`plan/implement/review/fix` on/off).
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

### 1) Runner (Host)

```powershell
cd D:\AI_Vibe\LoL\runner
.\start_runner.ps1
```

### 2) Orchestrator (Docker)

```powershell
cd D:\AI_Vibe\LoL\orchestrator
docker compose up --build
```

### 3) Open

- `http://localhost:8080`
