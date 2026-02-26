# Orchestrator (Docker)

The orchestrator provides:

1. Web UI for project-room workflow operations.
2. Workflow control plane (queue/run/cancel/stream).
3. Project settings + conversation + run persistence APIs.

It does **not** execute codex/gemini directly. Execution is delegated to the host Runner.

## Run

```powershell
cd D:\AI_Vibe\LoL\orchestrator
docker compose up --build
```

- URL: `http://localhost:8080`

## Environment

- `RUNNER_BASE_URL` (default: `http://host.docker.internal:8765`)
- `ORCH_ROOT_DIR` (default: `/workspace/LoL`)
- `ORCH_DATA_DIR` (default: `/app/data`)

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
