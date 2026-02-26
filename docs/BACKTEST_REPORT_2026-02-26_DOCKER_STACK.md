# Backtest Report - Docker Internal 5-Step Validation

- Generated: 2026-02-26T05:15:18Z
- Total: 5
- Passed: 5
- Failed: 0

| Step | Check | Result |
| --- | --- | --- |
| 1 | orchestrator_health | PASS |
| 2 | container_to_runner_health | PASS |
| 3 | runner_job_execution | PASS |
| 4 | workflow_execution | PASS |
| 5 | workflow_cancel | PASS |

## Scope

1. All tests were executed from inside `lol-orchestrator` container using `docker exec`.
2. Stack mode: `orchestrator + runner` in one Docker network.
3. Runner default mode: built-in mock agents (no external CLI dependency required).

## Artifacts

- `docs/backtest_results_2026-02-26_docker_stack.json`
