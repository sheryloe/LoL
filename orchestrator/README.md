# Orchestrator (Docker)

The orchestrator provides:

1. Web UI for project-room workflow operations.
2. Workflow control plane (queue/run/cancel/stream).
3. Project settings + conversation + run persistence APIs.

It does **not** execute codex/gemini directly. Execution is delegated to the `runner` service.

## Run

```powershell
cd D:\AI_Vibe\LoL\orchestrator
docker compose up --build
```

- URL: `http://localhost:8080`

## Compose Services

1. `orchestrator` (`:8080`)
2. `runner` (`:8765`)

Default wiring:

- `RUNNER_BASE_URL=http://runner:8765`
- `runner-home` named volume persists runner CLI auth state (`/root` in `lol-runner`).

## Environment

- `RUNNER_BASE_URL` (default: `http://runner:8765`)
- `ORCH_ROOT_DIR` (default: `/workspace/LoL`)
- `ORCH_DATA_DIR` (default: `/app/data`)

## Real CLI/Auth Setup (Optional)

Create `.env` from `.env.example` and set:

- `RUNNER_AGENT_MODE` (`mock` / `auto` / `real`)
- `CODEX_CMD`
- `GEMINI_CMD`
- `OPENAI_API_KEY`
- `GEMINI_API_KEY`

Default is strict real mode. If CLI/auth is missing, workflow start is blocked by preflight with actionable errors.

Recommended real command templates:

- `CODEX_CMD=codex exec --skip-git-repo-check --full-auto {prompt}`
- `GEMINI_CMD=gemini --prompt {prompt} --yolo`

Optional interactive login inside container:

```powershell
docker exec -it lol-runner codex login
```

Health check:

```powershell
curl http://localhost:8765/health
```

Strict preflight check:

```powershell
curl "http://localhost:8765/preflight/agents?cwd_relative=."
```

## Core Endpoints

- `POST /api/chat`
- `GET /api/workflow/{workflow_job_id}`
- `POST /api/workflow/{workflow_job_id}/cancel`
- `GET /api/workflow/stream/{workflow_job_id}`
- `GET /api/projects`
- `POST /api/projects`
- `GET/PUT/PATCH /api/projects/{project_id}/settings`
- `GET /api/projects/{project_id}/conversation`
- `GET /api/projects/{project_id}/runs`
- `GET /api/projects/{project_id}/runs/{workflow_job_id}`

## Data Layout

- `data/projects/<project_id>/settings.json`
- `data/projects/<project_id>/conversation.ndjson`
- `data/projects/<project_id>/runs/<workflow_job_id>.json`
- `data/journals/<session_id>.ndjson`
