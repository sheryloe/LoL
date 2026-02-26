# Backtest Report (2026-02-26)

## 요약

- 대상: `D:\AI_Vibe\LoL` (`runner` + `orchestrator`)
- 실행 시각: 2026-02-26 10:53:10
- 총 테스트: 22
- 통과: 21
- 실패: 1
- 원시 데이터: [backtest_results_2026-02-26.json](./backtest_results_2026-02-26.json)

## 테스트 환경

1. Runner를 로컬에서 테스트용 mock CLI로 실행
2. Mock CLI는 즉시 성공/지연(SLOW) 시나리오를 재현
3. Orchestrator는 TestClient 기반 API 검증
4. ORCH 데이터는 `orchestrator/data_backtest` 경로 사용

## 테스트 범위

### Runner

1. health 응답
2. git status 응답
3. codex job 생성
4. codex job 완료
5. job cancel
6. write 비활성 상태에서 git commit 차단
7. write 비활성 상태에서 git push 차단

### Orchestrator

1. health 응답
2. UI 루트 렌더
3. 프로젝트 생성
4. 프로젝트 설정 PUT
5. 프로젝트 목록 조회
6. 채팅 시작(`/api/chat`)
7. workflow 완료 상태 확인
8. conversation 조회
9. runs 목록 조회
10. run 상세 조회
11. workflow cancel 요청
12. workflow canceled 상태 확인
13. preflight fail-fast 확인
14. files 목록 조회
15. file 읽기

## 결과 상세

### PASS (핵심)

1. Runner의 기본 실행/취소/권한 차단 동작 정상
2. Orchestrator의 프로젝트 설정 CRUD 정상
3. 채팅 시작 -> workflow 실행/완료 정상
4. conversation/runs 영속화 조회 정상
5. workflow cancel 요청 및 canceled 상태 전환 정상
6. 파일 브라우저 API 정상

### FAIL

1. `orch_preflight_fail_fast`  
   기대: Runner URL 비정상(`http://127.0.0.1:9`)일 때 짧은 시간 내 `failed`  
   실제: 약 25.76초 경과 후에도 `running` 잔류

## 실패 원인 가설

1. preflight 실패 경로에서 예외 전파 또는 상태 전이 타이밍 문제가 있음
2. 비정상 endpoint 처리 시 `WorkflowManager`의 실패 이벤트 emit이 누락될 가능성

## 개선 액션

1. `RunnerClient.preflight` 타임아웃/예외 케이스 상세 로깅 추가
2. `_execute`에서 preflight 예외 발생 즉시 `failed` 상태 강제 전환 보장
3. preflight 실패 전용 회귀 테스트를 CI에 추가

