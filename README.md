# LoL 로컬 오케스트레이션

## 구성

- `runner/`: Windows Host Runner (FastAPI)
- `orchestrator/`: Docker Orchestrator (Web UI + workflow + session journal + file browser)

## 아키텍처 요약

- 컨테이너(`orchestrator`)는 `codex`/`gemini` CLI를 직접 실행하지 않습니다.
- Windows Host의 `runner`가 `codex`/`gemini`/`git`를 subprocess로 실행합니다.
- 오케스트레이션 루프:
  - Gemini(Plan) -> Codex(Implement) -> Gemini(Review) -> Codex(Fix, 선택)
- 실행/파일 작업 기준 루트:
  - `D:\AI_Vibe\LoL` 하위만 허용

## 실행 순서

1. Host Runner 실행

```powershell
cd D:\AI_Vibe\LoL\runner
.\start_runner.ps1
```

2. Orchestrator 실행

```powershell
cd D:\AI_Vibe\LoL\orchestrator
docker compose up --build
```

3. 웹 UI 접속

- `http://localhost:8080`

## 주요 API

### Host Runner

- `POST /run/codex`
- `POST /run/gemini`
- `GET /stream/{job_id}` (SSE)
- `GET /git/status`
- `POST /git/commit` (`RUNNER_WRITE_ENABLED=true`일 때만)
- `POST /git/push` (`RUNNER_WRITE_ENABLED=true`일 때만)

### Orchestrator

- `POST /api/chat` (채팅 입력으로 워크플로 시작)
- `GET /api/workflow/stream/{workflow_job_id}` (단계별 스트림)
- `GET /api/files`, `GET /api/file` (파일 브라우저)
- `GET /api/session/{session_id}/journal` (세션 저널 조회)

## 보안 제약

- 절대 경로, 드라이브 경로, path traversal(`..`) 입력은 차단됩니다.
- Runner의 모든 `cwd_relative`는 루트(`D:\AI_Vibe\LoL`) 하위로 강제됩니다.

## 문서

- 대화 로그: `CONVERSATION_LOG.md`
