# Backtest Report - Auth UI Flow

- Generated: 2026-02-26
- Scope: Docker internal verification (`docker exec` from `lol-orchestrator`)

| Check | Result |
| --- | --- |
| `GET /api/runner/auth/urls` | PASS |
| `GET /api/runner/auth/runtime` | PASS |
| `POST /api/runner/auth/runtime-keys` | PASS |
| CA bundle mount + preflight check | PASS |
| `GET /api/runner/preflight` after runtime keys | PASS (`ready=true`) |
| `POST /api/runner/auth/codex/device/start` | PASS |
| `GET /api/runner/jobs/stream/{job_id}` proxy | PASS |
| Device-auth failure message surfaced to UI logs | PASS |

## Notes

1. Auth buttons now open provider login pages directly from UI.
2. Runtime key save flow is connected and immediately reflected in preflight readiness.
3. Codex device-auth command starts via UI/API; if Cloudflare/network blocks occur, UI now guides user to API key flow.
4. Final real success-path requires valid credentials and allowed outbound access to provider auth endpoints.

## Artifact

- `docs/backtest_results_2026-02-26_auth_ui_flow.json`
