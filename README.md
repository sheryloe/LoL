# Vibe_Cowork_Thinking

프로젝트별 설정과 실행 로그를 유지하면서 Codex/Gemini 작업 흐름을 오케스트레이션하는 실험적 워크스페이스입니다.

- Repository: https://github.com/sheryloe/Vibe_Cowork_Thinking
- Landing page: https://sheryloe.github.io/Vibe_Cowork_Thinking/
- Audience: AI 협업 오케스트레이션, Codex/Gemini 러너, 워크플로 자동화에 관심 있는 개발자

## Search Summary
Runner와 Orchestrator로 구성한 AI 협업 워크플로 저장소

## Problem This Repo Solves
AI 코딩 보조 도구를 프로젝트 단위로 운영하려면 실행 로그, 권한, 워크플로 단계, Git 연동을 함께 다뤄야 합니다.

## Key Features
- Runner와 Orchestrator를 분리한 실행 구조
- 프로젝트별 `settings.json`, conversation, run, journal 기록 축적
- Plan -> Implement -> Review -> Fix 흐름 추적
- Git status/commit/push와 연동 가능한 Host Runner API

## User Flow
- Runner 실행
- Orchestrator 기동 후 프로젝트 룸 선택
- 워크플로 스트림과 로그, Git 상태를 함께 확인

## Tech Stack
- FastAPI
- Docker Compose
- Web UI
- Runner/Orchestrator architecture

## Quick Start
- `runner/start_runner.ps1`로 Host Runner를 실행합니다.
- `orchestrator`에서 `docker compose up --build`로 오케스트레이터를 실행합니다.
- 브라우저에서 `http://localhost:8080`으로 접속합니다.

## Repository Structure
- `runner/`: Windows Host에서 codex/gemini/git 실행
- `orchestrator/`: Web UI와 워크플로 상태 관리
- `docs/`: TODO, 백테스트, 결과 문서

## Search Keywords
`AI orchestration workspace`, `codex runner orchestrator`, `project room workflow`, `AI 협업 워크플로`, `runner orchestrator`

## FAQ
### Vibe_Cowork_Thinking은 무엇을 실험하나요?
AI 코딩 도구를 프로젝트 룸과 실행 워크플로 단위로 관리하는 방식을 실험합니다.

### Runner는 어떤 역할을 하나요?
Windows Host에서 codex, gemini, git 명령을 제어하고 작업 상태를 반환합니다.

### 왜 로그 구조가 중요한가요?
conversation, runs, journals를 분리 저장해야 프로젝트 단위 추적과 재현이 가능하기 때문입니다.
