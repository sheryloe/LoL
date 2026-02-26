# TODO Roadmap (Priority)

기준: 2026-02-26 현재 구현 상태 + 백테스트 결과

## P0 (즉시)

1. `Step 09` preflight fail-fast 버그 수정  
   증상: runner base URL 불능 시 workflow가 `failed`로 즉시 전환되지 않고 `running` 잔류
2. `Step 10` cancel 안정성 보강  
   목표: 취소 요청 후 추가 step 실행 0건 보장
3. preflight/cancel 회귀 테스트 자동화 추가

## P1 (단기)

4. `Step 11` 프로젝트별 파이프라인 구성화 (단계 on/off + 순서)
5. `Step 12` 프로젝트별 CLI 템플릿 실반영
6. `Step 13` 타임라인 UI 통합 (이벤트/아티팩트/상태)
7. `Step 14` run별 파일 diff 뷰어
8. `Step 15` Git Guarded Flow (status -> commit draft -> commit -> push)

## P2 (중기)

9. `Step 16` 프로젝트 권한 정책 확장 (`read_only`, `write_limited`, `full_write`)
10. `Step 17` 인증/비밀값 체계 개선 (정적 토큰 제거)
11. `Step 18` 감사 로그 스키마 + API + UI
12. `Step 19` 테스트 계층 확장 (unit/integration/e2e/failure)
13. `Step 20` 운영 관측성(메트릭/구조 로그/추적 ID)

## 완료된 항목

1. `Step 01` 단일 코드베이스 기준 정리 (`D:\\AI_Vibe\\LoL`)
2. `Step 02` ProjectRoom 모델 + schema_version
3. `Step 03` 프로젝트 설정 영속 저장소
4. `Step 04` 설정 API (list/create/get/put/patch)
5. `Step 05` 설정 UI 패널
6. `Step 06` `/api/chat` 설정 기반 해석
7. `Step 07` 프로젝트별 conversation 영속화
8. `Step 08` 프로젝트별 run 상태 영속화

