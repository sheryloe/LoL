# Runner Service

The runner executes codex/gemini/git commands and exposes API endpoints used by orchestrator.

## Runtime

- Default in Docker Compose as `lol-runner` on port `8765`
- Root workspace: `/workspace/LoL`
- Docker image includes `codex` and `gemini` CLIs.

## Real CLI Mode

Runner mode control:

- `RUNNER_AGENT_MODE=real`: strict real mode (default). Missing CLI/auth blocks workflow.
- `RUNNER_AGENT_MODE=auto`: real-first mode without mock fallback.
- `RUNNER_AGENT_MODE=mock`: debug-only fallback mode.

Optional explicit environment variables:

- `CODEX_CMD` (example: `codex exec --skip-git-repo-check --full-auto {prompt}`)
- `GEMINI_CMD` (example: `gemini --prompt {prompt} --yolo`)
- `OPENAI_API_KEY`
- `GEMINI_API_KEY`
- `RUNNER_CA_CERT_FILE` (optional, custom CA bundle path for TLS trust)

`CODEX_CMD` and `GEMINI_CMD` support `{prompt}` placeholder.

If no `{prompt}` exists, default runner command appends prompt only for non-explicit defaults.
Explicit `command_template` requests are executed as-is.

Health endpoint (`GET /health`) includes runtime diagnosis:

- `agent_mode`
- `codex_source`
- `gemini_source`
- `codex_available`
- `gemini_available`
- `openai_api_key_present`
- `gemini_api_key_present`

Strict readiness endpoint (`GET /preflight/agents`) returns:

- `ready`
- `issues[]` with `code`, `message`, `action`
- `checks` (CLI, command resolution, auth, git status)

Auth helper endpoints:

- `GET /auth/urls`
- `GET /auth/runtime`
- `POST /auth/runtime-keys`
- `POST /auth/codex/device/start`

If Codex device-auth is blocked by Cloudflare/network policy, use API-key flow through `/auth/runtime-keys`.

## API

### Execution

- `POST /run/codex`
- `POST /run/gemini`
- `GET /jobs/{job_id}`
- `POST /jobs/{job_id}/cancel`
- `GET /stream/{job_id}`

### Git

- `GET /git/status`
- `POST /git/commit` (`RUNNER_WRITE_ENABLED=true` required)
- `POST /git/push` (`RUNNER_WRITE_ENABLED=true` required)

## Security Model

1. `cwd_relative` is constrained under `RUNNER_ROOT_DIR`.
2. Absolute paths and traversal attempts are blocked.
3. Commit/push are blocked in read-only mode.
