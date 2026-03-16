# Vibe_Cowork_Thinking

`Vibe_Cowork_Thinking`은 Codex/Gemini 같은 AI 도구를 프로젝트 단위로 운영하기 위한 Runner + Orchestrator 워크스페이스입니다.

- 저장소: `https://github.com/sheryloe/Vibe_Cowork_Thinking`
- GitHub Pages: `https://sheryloe.github.io/Vibe_Cowork_Thinking/`

## 서비스 개요

- 실행 로그, 대화 이력, 작업 단계, Git 흐름을 한 프로젝트 방 안에서 추적합니다.
- 에이전트 작업을 “생성형 채팅”이 아니라 “운영 가능한 작업 파이프라인”으로 다루는 것이 목표입니다.

## 핵심 기능

- Runner와 Orchestrator 분리 구조
- 프로젝트별 `settings.json`, conversation, runs, journals 관리
- Plan -> Implement -> Review -> Fix 흐름 추적
- Host Runner API를 통한 git/status/commit 연동

## 기술 스택

- FastAPI
- Docker Compose
- Web UI
- Runner / Orchestrator architecture

## 실행 방법

```powershell
runner/start_runner.ps1
```

```bash
cd orchestrator
docker compose up --build
```

기본 접속 주소:

- UI: `http://localhost:8080`

## 디렉터리

- `runner/`: Windows host에서 codex, gemini, git 실행
- `orchestrator/`: Web UI와 상태 관리
- `docs/`: TODO, 보고서, 결과 문서

## 다음 단계

- 실행 재개/재시도 흐름
- 산출물 diff 비교
- 권한 정책과 프로젝트 템플릿 추가
