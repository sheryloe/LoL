# Backtest Report - Strict Preflight Gate

- Generated: 2026-02-26
- Scope: Docker internal only (`docker exec` from `lol-orchestrator`)

| Check | Result |
| --- | --- |
| `/api/runner/preflight` returns `ready=false` with actionable auth issues | PASS |
| `/api/chat` is blocked with HTTP `412` when runner is not ready | PASS |
| `/run/codex` is blocked with HTTP `412` and install/auth guidance | PASS |

## Key evidence

1. `CODEX_AUTH_MISSING` with action `docker exec -it lol-runner codex login`.
2. `GEMINI_AUTH_MISSING` with action to set `GEMINI_API_KEY` or Gemini auth config.
3. Workflow start is denied before queuing (`RUNNER_PREFLIGHT_FAILED`).

## Artifact

- `docs/backtest_results_2026-02-26_strict_preflight.json`
