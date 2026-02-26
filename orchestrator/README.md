# Web Orchestrator v1 (Skeleton)

Minimal, extensible orchestrator for a Telegram-based AI Assistant backend execution layer.

## Core Principles

- Ollama runs on local Windows host only (not in Docker).
- Execution workers are stateless and synchronous.
- Artifact-first: every run writes output to disk immediately.
- Default mode is read-only.
- Any write operation requires `write_enabled=true`.

## Tech Stack

- Backend: FastAPI (Python 3.11+)
- Frontend: Jinja2 templates + minimal CSS
- Storage: JSON + Markdown files only
- Containerization: Docker / docker-compose

## Directory Layout

```text
orchestrator/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── models/
│   ├── routers/
│   ├── services/
│   ├── utils/
│   └── workers/
├── templates/
├── static/
├── data/
│   └── projects/
├── docker/
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── .auth/
├── mvp/
│   ├── orchestrator.py
│   ├── design_spec.example.json
│   └── README.md
└── README.md
```

Each project has this structure:

```text
data/projects/<project_id>/
├── spec/
├── tasks/
├── codex_outputs/
├── gemini_outputs/
├── artifacts/
└── discussion/
```

## Configuration (`app/config.py`)

Required safety defaults:

- `TREND_DAILY_LIMIT = 20`
- `WRITE_ENABLED_DEFAULT = False`
- `UI_ADMIN_TOKEN = "change-me"`
- `OLLAMA_BASE_URL = "http://localhost:11434"`
- `BAD_REQUEST_RETRY_COUNT = 2`
- `BAD_REQUEST_RETRY_DELAY_SECONDS = 1.0`
- `NOTION_TOKEN = ""` (optional)
- `NOTION_PARENT_PAGE_ID = ""` (optional)

Docker-compose env template:

- Copy `.env.example` to `.env`

Default Ollama model:

- `qwen2.5:7b-instruct`

## Worker Architecture

- `BaseWorker`
- `OllamaWorker` (HTTP)
- `CodexWorker` (subprocess)
- `GeminiWorker` (subprocess)

Bad-request retry:

- Workers automatically retry when they detect `400 / Bad Request` patterns.
- Retry attempts and delay logs are written into output markdown artifacts.

Execution flow:

1. Validate target project.
2. Validate write permission (`write_enabled`).
3. Run worker synchronously.
4. Save output Markdown to worker folder.
5. Save execution metadata JSON to `artifacts/`.

## API Endpoints

- `GET /health`
- `GET /api/projects`
- `POST /api/projects`
- `GET /api/projects/{project_id}`
- `POST /api/projects/{project_id}/notion/publish`
- `GET /api/projects/{project_id}/workers`
- `GET /api/projects/{project_id}/workers/auth/status`
- `POST /api/projects/{project_id}/workers/{worker_name}/run`

## MVP: Spec -> RAG -> Multi-CLI

Required MVP orchestrator entrypoint:

- `mvp/orchestrator.py`

Core functions implemented:

1. `parse_spec(file_path)`
2. `get_rag_context(query)`
3. `dispatch_to_cli(agent_type, task, context)`
4. `run_orchestrator()`

Behavior:

- Reads `design_spec.json` style input (`Task_A`, `Task_B` or `tasks[]`)
- Builds local-file-based dummy RAG context (interface ready for vector DB swap)
- Dispatches tasks to Gemini/Codex via `asyncio.create_subprocess_exec` list args (shell injection-safe)
- Runs independent tasks in parallel with `asyncio.gather`; dependency-linked tasks run sequentially
- Detects missing CLI binaries and returns explicit install/path errors
- Uses session-based CLI auth mount only (no runtime API-key injection)
- Handles per-task failures and still writes run logs (`/app/data/mvp_runs`)

## Web UI

- `/` project list + create form
- `/projects/{project_id}` tab view
- `/projects/{project_id}` 안에서 Notion 발행 폼 제공
- Form submission charset is fixed to UTF-8 (`accept-charset="UTF-8"`).

Project input rule:

- `project_id` is a filesystem-safe identifier (3-64 chars, `a-zA-Z0-9_-` only).
- Korean text should be entered in `title`.

Tabs:

- Spec
- Tasks
- Codex Outputs
- Gemini Outputs
- Discussion
- Artifacts

Notion write style guide:

- [NOTION_STEP_PLAYBOOK.md](./docs/NOTION_STEP_PLAYBOOK.md)
- Publisher script (400 auto-retry):
  - `scripts/notion_publish_step.py`
  - Example:
    - `python scripts/notion_publish_step.py --token <NOTION_TOKEN> --parent-page-id <PAGE_ID> --title \"RAG Step 01\" --content-file docs/NOTION_STEP_PLAYBOOK.md`

## Local Run

```bash
cd orchestrator
python -m venv .venv
. .venv/Scripts/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Docker Run

```bash
cd orchestrator
cp .env.example .env
docker compose up --build
```

Note: This compose file runs orchestrator only. Ollama is expected on the local host at `http://localhost:11434`.

Session/auth mounting:

- Configure host session paths in `.env`:
  - `HOST_GH_CONFIG_DIR`
  - `HOST_CODEX_CONFIG_DIR`
  - `HOST_GEMINI_CONFIG_DIR`
- Compose mounts those into container (read-write; login state is persisted on host):
  - `/root/.config/gh`
  - `/root/.codex`
  - `/root/.config/gemini`

CLI login check and commands:

- Auth status API: `GET /api/projects/{project_id}/workers/auth/status`
- If Codex is not logged in:
  - `docker exec -it web-orchestrator-v1 codex login --device-auth`
- If Gemini is not logged in:
  - `docker exec -it web-orchestrator-v1 gemini`
  - Then run `/auth` in Gemini CLI.

Worker execution is blocked with `412` until CLI login is ready.

TLS/self-signed certificate troubleshooting:

- Symptom:
  - `self-signed certificate in certificate chain`
  - Gemini OAuth/token request fails (`oauth2.googleapis.com/token`)
- Fix in this stack:
  - Mount host CA bundle to `/certs` via compose
  - Set `TLS_CA_CERT_FILE=/certs/eprism.pem` (this environment verified)
  - Exported to runtime:
    - `NODE_EXTRA_CA_CERTS`
    - `SSL_CERT_FILE`
    - `REQUESTS_CA_BUNDLE`

Run MVP orchestrator inside container:

```bash
docker compose run --rm orchestrator \
  python /app/mvp/orchestrator.py \
  --spec /workspace/orchestrator/mvp/design_spec.example.json \
  --workspace-dir /workspace \
  --rag-dir /workspace \
  --dry-run
```

Parallel execution example:

```bash
docker compose run --rm orchestrator \
  python /app/mvp/orchestrator.py \
  --spec /workspace/orchestrator/mvp/design_spec.example.json \
  --workspace-dir /workspace \
  --rag-dir /workspace \
  --parallel \
  --dry-run
```

## Example API Calls

Create project (write-enabled):

```bash
curl -X POST http://localhost:8000/api/projects \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "demo_project",
    "title": "Demo",
    "write_enabled": true
  }'
```

Run Ollama worker:

```bash
curl -X POST http://localhost:8000/api/projects/demo_project/workers/ollama/run \
  -H "Content-Type: application/json" \
  -d '{
    "write_enabled": true,
    "task": {
      "prompt": "Summarize this architecture.",
      "model": "qwen2.5:7b-instruct"
    }
  }'
```

Publish step log to Notion:

```bash
curl -X POST http://localhost:8000/api/projects/demo_project/notion/publish \
  -H "Content-Type: application/json" \
  -d '{
    "notion_token": "secret_xxx",
    "parent_page_id": "31361b8ed53c81ae94a6e9c6e74dc6ae",
    "step_title": "Step 02 - Retrieval Quality",
    "one_line_summary": "랭킹 품질 개선",
    "background": "검색 정확도 이슈",
    "core_concepts": "가중치와 중복 제거",
    "implementation_details": "서비스 코드 수정 내용",
    "test_notes": "docker 내부 검증 결과",
    "troubleshooting": "400 응답 시 자동 재시도",
    "next_steps": "semantic retrieval 도입"
  }'
```

## GitHub Push (Target Repository)

Repository target:

- https://github.com/sheryloe/LoL.git

Suggested commands:

```bash
git init
git remote add origin https://github.com/sheryloe/LoL.git
git add .
git commit -m "feat: scaffold web orchestrator v1"
git branch -M main
git push -u origin main
```
