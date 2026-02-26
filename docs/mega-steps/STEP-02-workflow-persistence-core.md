# STEP 02 - Workflow and Persistence Core

## 목표

- 채팅 요청이 workflow 단계(`plan -> implement -> review -> fix(optional)`)를 일관되게 타도록 정형화.
- 프로젝트 설정/대화/실행 상태를 영속 저장해 재시작 후에도 문맥 유지.

## 핵심 구현

1. Project room model 정비.
2. Settings 저장/조회 API 및 UI 연결.
3. Conversation log, run state, artifact 저장 파이프라인 구축.
4. 취소/중단 제어 로직(후속 step 실행 차단) 반영.

## API/데이터 예시

```json
{
  "project_id": "room-main",
  "session_id": "room-main",
  "message": "현재 이슈 원인 분석 후 수정안 제시",
  "write_enabled": true
}
```

```json
{
  "project_id": "room-main",
  "status": "completed",
  "steps": [
    {"name": "plan", "status": "done"},
    {"name": "implement", "status": "done"},
    {"name": "review", "status": "done"}
  ]
}
```

## 검증

- 프로젝트 생성 -> 설정 저장 -> 채팅 실행 -> 산출물 저장까지 end-to-end 확인.
- 재기동 후 동일 `project_id`로 이전 대화/실행 기록 재조회 확인.
- cancel 시 이후 단계가 실제로 멈추는지 확인.

## 결과

- "대화형 UI"와 "실행 파이프라인"이 분리되지 않고, 프로젝트 단위 상태로 안정적으로 연결됐다.
- 이후 보안/실행 강제 단계에서 차단/가이드 정책을 적용할 기반이 갖춰졌다.
