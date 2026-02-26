# STEP 03 - Real Execution and Reliability Hardening

## 목표

- mock 우회 없이 **실제 CLI/auth 준비가 안 되면 실행 자체를 차단**.
- Cloudflare 400 등 인증 실패 상황에서 사용자가 바로 복구할 수 있는 UI/가이드 제공.
- bad request 계열 오류에 대한 재시도 정책을 코드로 고정.

## 핵심 변경

1. Runner preflight fast-fail 도입.
2. `/api/chat` 시작 전 readiness 검증 + HTTP 412 차단.
3. Auth UI(브라우저 열기/키 저장/상태 확인) 보강.
4. worker bad request 재시도 로직 추가.

## 실패/복구 시나리오

```text
증상: 인증 페이지에서 Cloudflare 400
대응:
1) UI에서 OpenAI/Gemini 키 저장
2) Runner readiness 재검사
3) preflight 통과 후 실행 재시도
```

## 샘플: preflight 체크

```bash
curl "http://localhost:8765/preflight/agents?cwd_relative=."
```

예상 필드:

- `agent_mode`
- `codex_source`
- `gemini_source`
- `openai_api_key_present`
- `gemini_api_key_present`

## 샘플: 차단 응답(의도된 동작)

```json
{
  "detail": {
    "code": "RUNNER_NOT_READY",
    "message": "CLI/auth prerequisites are not satisfied",
    "checks": ["CODEX_AUTH_MISSING", "GEMINI_AUTH_MISSING"]
  }
}
```

## 결과

- "어거지 실행" 대신 "사전 조건 충족 후 실행"으로 운영 안정성이 크게 향상.
- 장애 시 원인과 다음 액션이 UI에 즉시 노출되어 복구 속도가 빨라졌다.
