# Backtest Report - Docker Internal 5-Step Validation (CLI-Ready)

- Generated: 2026-02-26T05:33:15Z
- Total: 5
- Passed: 5
- Failed: 0

| Step | Check | Result |
| --- | --- | --- |
| 1 | orchestrator_health | PASS |
| 2 | runner_health | PASS |
| 3 | runner_direct_run | PASS |
| 4 | workflow_run | PASS |
| 5 | workflow_cancel | PASS |

## Scope

1. All checks were executed from inside `lol-orchestrator` using `docker exec`.
2. Runner image now contains `codex` and `gemini` CLIs.
3. Current runtime was `RUNNER_AGENT_MODE=auto` with no API keys, so command source was auto-mock fallback (`codex_available=True`, `gemini_available=True`).

## Artifacts

- `docs/backtest_results_2026-02-26_docker_cli_mode.json`
