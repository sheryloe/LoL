# Runner Service

The runner executes codex/gemini/git commands and exposes API endpoints used by orchestrator.

## Runtime

- Default in Docker Compose as `lol-runner` on port `8765`
- Root workspace: `/workspace/LoL`
- Docker image includes `codex` and `gemini` CLIs.

## Default Mode (No CLI Required)

If `CODEX_CMD` and `GEMINI_CMD` are empty, runner uses built-in mock agents:

- `runner/app/mock_agent.py`

This keeps end-to-end workflow stable for development and tests.

## Real CLI Mode

Runner mode control:

- `RUNNER_AGENT_MODE=mock`: always mock
- `RUNNER_AGENT_MODE=auto`: real only when binary + API key exist
- `RUNNER_AGENT_MODE=real`: force real defaults (`codex`, `gemini`)

Optional explicit environment variables:

- `CODEX_CMD` (example: `codex exec --skip-git-repo-check --full-auto {prompt}`)
- `GEMINI_CMD` (example: `gemini --prompt {prompt} --yolo`)
- `OPENAI_API_KEY`
- `GEMINI_API_KEY`

`CODEX_CMD` and `GEMINI_CMD` support `{prompt}` placeholder.

If no `{prompt}` exists:

- default runner command will append prompt only for non-explicit defaults
- explicit command template requests are executed as-is

Health endpoint (`GET /health`) includes runtime diagnosis:

- `agent_mode`
- `codex_source`
- `gemini_source`
- `codex_available`
- `gemini_available`
- `openai_api_key_present`
- `gemini_api_key_present`

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
