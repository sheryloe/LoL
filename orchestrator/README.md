# Orchestrator (Docker)

Orchestrator는 Web UI와 워크플로 제어를 담당하며, 실제 CLI 실행은 Runner에 위임합니다.

## 실행

```powershell
cd D:\AI_Vibe\LoL\orchestrator
docker compose up --build
```

- 기본 접속: `http://localhost:8080`

## 환경 변수

- `RUNNER_BASE_URL` (default: `http://host.docker.internal:8765`)
- `ORCH_ROOT_DIR` (default: `/workspace/LoL`)
- `ORCH_DATA_DIR` (default: `/app/data`)

## 주요 기능

1. 채팅 입력 기반 워크플로 실행 (`/api/chat`)
2. 프로젝트 설정 관리 (`/api/projects`, `/api/projects/{id}/settings`)
3. 워크플로 상태/스트림 조회 (`/api/workflow/{id}`, `/api/workflow/stream/{id}`)
4. 워크플로 취소 (`/api/workflow/{id}/cancel`)
5. 프로젝트별 대화/실행 이력 조회
- `/api/projects/{id}/conversation`
- `/api/projects/{id}/runs`
6. 파일 브라우저 (`/api/files`, `/api/file`)

## 데이터 저장

- 프로젝트 설정: `data/projects/<project_id>/settings.json`
- 프로젝트 대화 이력: `data/projects/<project_id>/conversation.ndjson`
- 프로젝트 실행 이력: `data/projects/<project_id>/runs/<workflow_job_id>.json`
- 세션 저널: `data/journals/<session_id>.ndjson`

