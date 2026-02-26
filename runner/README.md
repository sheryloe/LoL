# Host Runner (Windows)

The runner executes codex/gemini/git commands on Windows host and exposes a small API for orchestrator.

## Run

```powershell
cd D:\AI_Vibe\LoL\runner
.\start_runner.ps1
```

## Environment

- `RUNNER_ROOT_DIR` (default: `D:\AI_Vibe\LoL`)
- `RUNNER_WRITE_ENABLED` (default: `false`)
- `CODEX_CMD` (default: `codex`)
- `GEMINI_CMD` (default: `gemini`)

`CODEX_CMD` and `GEMINI_CMD` support tokenized templates and optional `{prompt}` placeholder.

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
