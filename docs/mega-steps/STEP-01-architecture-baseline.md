# STEP 01 - Architecture Baseline

## 목표

- 작업 기준 폴더를 단일화하고(`D:\AI_Vibe\LoL`) 중복 경로 편집 리스크 제거.
- Orchestrator + Runner를 Docker 기준으로 고정해 실행 재현성 확보.
- "한 채팅방 = 한 프로젝트" 모델을 팀 공통 규칙으로 확정.

## 핵심 결정

1. 코드/문서/데이터의 Source of Truth를 `LoL` 저장소 하나로 통일.
2. 실행 경로를 `docker compose` 기준으로 정의하고 로컬 임시 실행 의존성 축소.
3. README에 TODO와 백테스트 리포트 링크를 항상 노출해 상태 가시성 확보.

## 구현 포인트

- `orchestrator`와 `runner`를 분리 서비스로 운영.
- 프로젝트별 데이터 저장: `data/projects/<project_id>/...`.
- 저널/아티팩트를 파일로 남기는 artifact-first 정책 유지.

## 검증

- Docker 스택 기동 후 `http://localhost:8080` UI 접근 확인.
- Runner health와 Orchestrator API 연결 확인.
- README 링크에서 backtest json/md 직접 열람 가능 확인.

## 샘플

```powershell
cd D:\AI_Vibe\LoL\orchestrator
docker compose up --build
```

```text
data/projects/room-main/
├─ conversations/
├─ runs/
├─ artifacts/
└─ rag_index.json
```

## 결과

- 팀이 같은 기준 경로/실행 방식으로 움직이게 되었고, 이후 단계(워크플로/보안/RAG) 변경의 충돌 비용이 줄었다.
