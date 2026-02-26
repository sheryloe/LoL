# Notion Step Log Playbook

Reference style target: long-form technical post with clear flow:
- Background and objective first
- Concept/architecture explanation
- Implementation steps and code evidence
- Test commands and actual results
- Trouble cases and fixes
- Next action items

## Recommended Page Structure

1. `한 줄 요약`
- What this step changed and why it matters.

2. `문제 배경`
- Why the existing flow was insufficient.
- Constraints and assumptions.

3. `핵심 개념 정리`
- Key architecture and data flow.
- Any glossary needed for readers.

4. `구현 상세`
- Files changed and exact intent.
- Before/after behavior.

5. `코드 예시`
- Minimal reproducible snippets.
- Endpoint request/response examples.

6. `검증`
- Environment (docker/container names).
- Commands executed.
- Expected vs actual output.

7. `트러블슈팅`
- Error message
- Root cause
- Fix
- Re-test result

8. `다음 단계`
- Priority-ordered follow-ups.

## 400 Bad Request Handling Policy

When execution hits 400-like failures:

1. Retry automatically up to `BAD_REQUEST_RETRY_COUNT`.
2. Use incremental wait:
- `BAD_REQUEST_RETRY_DELAY_SECONDS * attempt`
3. Log retry traces in artifacts:
- attempt number
- reason
- wait duration

If retries still fail:

1. Persist full stderr/response body.
2. Mark run as failed with explicit root-cause hint.
3. Keep the troubleshooting section in the Notion page updated with that evidence.
