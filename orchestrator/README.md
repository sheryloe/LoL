# Orchestrator (Docker)

컨테이너에는 `codex`/`gemini` CLI가 없고 실행하지 않습니다.
Orchestrator는 `RUNNER_BASE_URL`로 Windows Host Runner를 호출합니다.

## Run

```powershell
cd D:\AI_Vibe\LoL\orchestrator
docker compose up --build
```

기본 접속: `http://localhost:8080`

## Environment

- `RUNNER_BASE_URL` (default: `http://host.docker.internal:8765`)
- `ORCH_ROOT_DIR` (default in container: `/workspace/LoL`)
- `ORCH_DATA_DIR` (default in container: `/app/data`)

## Features

- Chat input -> workflow execution
- 단계별 스트림 로그(SSE)
- 협업 루프: Gemini Plan -> Codex Implement -> Gemini Review -> Codex Fix(optional)
- 패널: Plan / Tasks / Patch / Review / Files / Git
- 세션 저널(`data/journals/*.ndjson`)
- 파일 브라우저(루트 하위 경로만 허용)
