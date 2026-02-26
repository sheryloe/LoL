# LoL Orchestration Workspace

`LoL`은 `채팅방 = 프로젝트(Project Room)` 모델을 중심으로, Runner와 Orchestrator가 협업해 AI 개발 워크플로를 실행하는 저장소입니다.

## 핵심 목표

1. 프로젝트별 설정으로 실행 컨텍스트를 고정한다.
2. 대화/실행 상태를 프로젝트 단위로 영속화한다.
3. 단계형 워크플로(Plan -> Implement -> Review -> Fix)를 추적 가능하게 운영한다.

## 구성

- `runner/`  
  Windows Host에서 `codex/gemini/git`를 subprocess로 실행하는 FastAPI 서비스
- `orchestrator/`  
  Web UI + Workflow 오케스트레이션 + Project Room 설정/로그 관리
- `docs/`  
  TODO, 백테스트 보고서, 결과 JSON

## 아키텍처 요약

1. 사용자가 Orchestrator UI에서 `project_id` 기준으로 요청 입력
2. Orchestrator가 프로젝트 설정(`settings.json`)으로 실행 파라미터 해석
3. WorkflowManager가 Runner로 단계별 실행 요청
4. 결과를 아래로 저장
- conversation: `data/projects/<project_id>/conversation.ndjson`
- runs: `data/projects/<project_id>/runs/<workflow_job_id>.json`
- journals: `data/journals/<session_id>.ndjson`

## 빠른 실행

### 1) Runner 실행 (Host)

```powershell
cd D:\AI_Vibe\LoL\runner
.\start_runner.ps1
```

### 2) Orchestrator 실행

```powershell
cd D:\AI_Vibe\LoL\orchestrator
docker compose up --build
```

### 3) 접속

- `http://localhost:8080`

## 현재 제공 기능

### Project Room / Settings

- 프로젝트 생성/조회/수정 API
- 프로젝트 설정 UI 패널
- `project_id` 기준 기본 실행값 해석

### Workflow

- 채팅 입력으로 워크플로 시작 (`/api/chat`)
- 단계 스트림 조회 (`/api/workflow/stream/{id}`)
- 워크플로 취소 API (`/api/workflow/{id}/cancel`)
- run 이력 조회 (`/api/projects/{id}/runs`)

### Logs / Trace

- 프로젝트별 conversation 이력 조회
- 세션별 journal 조회
- 파일 브라우저 (`/api/files`, `/api/file`)

### Runner

- `POST /run/codex`, `POST /run/gemini`
- `GET /jobs/{job_id}`, `POST /jobs/{job_id}/cancel`
- `GET /git/status`
- `POST /git/commit`, `POST /git/push` (`RUNNER_WRITE_ENABLED=true` 필요)

## 백테스트 결과 (2026-02-26)

- 결과: **22개 중 21개 PASS**
- 상세 리포트: [docs/BACKTEST_REPORT_2026-02-26.md](./docs/BACKTEST_REPORT_2026-02-26.md)
- 원시 결과: [docs/backtest_results_2026-02-26.json](./docs/backtest_results_2026-02-26.json)

### 확인된 이슈

- `orch_preflight_fail_fast` 실패  
  `RUNNER_BASE_URL` 비정상 상태에서 workflow가 `failed`로 빠르게 전환되지 않고 `running` 상태로 잔류.

## TODO (우선순위)

우선순위 전체 목록은 [docs/TODO.md](./docs/TODO.md) 참조.

### P0 (즉시)

1. `Step 09` preflight fail-fast 버그 수정  
   증상: runner base URL 불능 시 workflow가 `failed`로 즉시 전환되지 않고 `running` 잔류
2. `Step 10` cancel 안정성 보강  
   목표: 취소 요청 후 추가 step 실행 0건 보장
3. preflight/cancel 회귀 테스트 자동화 추가

### P1 (단기)

1. `Step 11` 프로젝트별 파이프라인 구성화 (단계 on/off + 순서)
2. `Step 12` 프로젝트별 CLI 템플릿 실행 반영
3. `Step 13` 타임라인 UI 통합 (이벤트/아티팩트/상태)
4. `Step 14` run별 파일 diff 뷰어
5. `Step 15` Git Guarded Flow (status -> commit draft -> commit -> push)

### P2 (중기)

1. `Step 16` 프로젝트 권한 정책 확장 (`read_only`, `write_limited`, `full_write`)
2. `Step 17` 인증/비밀값 체계 개선 (정적 토큰 제거)
3. `Step 18` 감사 로그 스키마 + API + UI
4. `Step 19` 테스트 계층 확장 (unit/integration/e2e/failure)
5. `Step 20` 운영 관측성 (메트릭/구조 로그/추적 ID)

## 개발 로드맵

- 단계별 로드맵: [ROADMAP_CHAT_PROJECT.md](./ROADMAP_CHAT_PROJECT.md)
