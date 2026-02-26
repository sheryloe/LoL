# LoL Multi-Agent Co-Worker (CLI Login Mode)

현재 저장소 기준 MVP는 `orchestrator` 서비스(포트 `8000`)입니다.  
핵심 목적은 **Codex + Gemini CLI 협업 채팅방 실행**입니다.

## Current State (2026-02-26)

- Git remote: `https://github.com/sheryloe/LoL.git`
- Main app: [`orchestrator`](./orchestrator)
- UI: `http://localhost:8000/`
- 인증 모델: API Key 주입이 아니라 **CLI 로그인 세션 공유 방식**
- Codex: `Logged in using ChatGPT` 확인됨 (환경별로 재로그인 가능)
- Gemini: `settings.json not found` 상태면 아직 로그인 전

## What Changed

1. `orchestrator`를 단일 워커 폼에서 **협업 채팅 실행(Codex+Gemini)** 구조로 확장.
2. CLI 설치/인증 상태를 API+UI에서 즉시 확인하도록 추가.
3. 인증 미완료 시 실행을 `412`로 차단하여 오작동 대신 명확한 오류를 반환.
4. Gemini/Codex TLS 인증서 이슈(`self-signed certificate in certificate chain`) 대응:
   `TLS_CA_CERT_FILE=/certs/eprism.pem` + `NODE_EXTRA_CA_CERTS/SSL_CERT_FILE/REQUESTS_CA_BUNDLE`.

## Quick Start

```powershell
cd D:\AI_Vibe\LoL\orchestrator
docker compose up --build -d
```

Open:

- `http://localhost:8000/`

Health:

```powershell
curl http://localhost:8000/health
```

## CLI Login Commands

Codex:

```powershell
docker exec -it web-orchestrator-v1 codex login --device-auth
docker exec web-orchestrator-v1 codex login status
```

Gemini:

```powershell
docker exec -it web-orchestrator-v1 gemini
# then run /auth inside gemini CLI
```

Auth status API:

```powershell
curl http://localhost:8000/api/projects/demo_project/workers/auth/status
```

## Documentation

- Orchestrator 상세 문서: [orchestrator/README.md](./orchestrator/README.md)
- Notion 발행 플레이북: [orchestrator/docs/NOTION_STEP_PLAYBOOK.md](./orchestrator/docs/NOTION_STEP_PLAYBOOK.md)
- MVP 오케스트레이터: [orchestrator/mvp/README.md](./orchestrator/mvp/README.md)

## TODO

1. Gemini 로그인 완료 후 협업 라운드 E2E 스모크 결과 문서화.
2. 협업 대화 세션 선택/필터 UI 개선.
3. 협업 실행 결과(diff, artifact 링크) 요약 뷰 추가.
4. 회귀 테스트 자동화(pytest + API integration).
