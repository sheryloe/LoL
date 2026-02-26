# Host Runner (Windows)

Runner는 Windows Host에서 `codex`, `gemini`, `git`를 subprocess로 실행하는 API 서비스입니다.

## 실행

```powershell
cd D:\AI_Vibe\LoL\runner
.\start_runner.ps1
```

## 환경 변수

- `RUNNER_ROOT_DIR` (default: `D:\AI_Vibe\LoL`)
- `RUNNER_WRITE_ENABLED` (default: `false`)
- `CODEX_CMD` (default: `codex`)
- `GEMINI_CMD` (default: `gemini`)

`CODEX_CMD`, `GEMINI_CMD`는 공백 분리 토큰으로 해석되며, `{prompt}` 플레이스홀더를 지원합니다.

예시:

```powershell
$env:GEMINI_CMD = "gemini --prompt {prompt}"
```

## API

### 실행

- `POST /run/codex`
- `POST /run/gemini`
- `GET /jobs/{job_id}`
- `POST /jobs/{job_id}/cancel`
- `GET /stream/{job_id}` (SSE)

### Git

- `GET /git/status`
- `POST /git/commit` (`RUNNER_WRITE_ENABLED=true` 필요)
- `POST /git/push` (`RUNNER_WRITE_ENABLED=true` 필요)

## 보안 제약

1. 모든 `cwd_relative`는 `RUNNER_ROOT_DIR` 하위로 제한
2. 절대 경로/드라이브 경로/path traversal(`..`) 차단
3. write 비활성 상태에서 commit/push 차단

