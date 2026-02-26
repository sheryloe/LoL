# Host Runner (Windows)

`runner`는 Windows Host에서 실행되며, `codex`/`gemini`/`git`를 실제 subprocess로 실행합니다.
컨테이너 내부에서는 CLI를 실행하지 않습니다.

## Endpoints

- `POST /run/codex`
- `POST /run/gemini`
- `GET /stream/{job_id}` (SSE)
- `GET /jobs/{job_id}`
- `GET /git/status`
- `POST /git/commit` (`RUNNER_WRITE_ENABLED=true`일 때만)
- `POST /git/push` (`RUNNER_WRITE_ENABLED=true`일 때만)

## Security

- 모든 `cwd_relative`는 `RUNNER_ROOT_DIR` 하위만 허용됩니다.
- 절대경로/드라이브 경로/path traversal(`..`)로 루트 밖 접근 시 요청이 거부됩니다.

## Run

```powershell
cd D:\AI_Vibe\LoL\runner
.\start_runner.ps1
```

### Optional env vars

- `RUNNER_ROOT_DIR` (default: `D:\AI_Vibe\LoL`)
- `RUNNER_WRITE_ENABLED` (default: `false`)
- `CODEX_CMD` (default: `codex`)
- `GEMINI_CMD` (default: `gemini`)

`CODEX_CMD`, `GEMINI_CMD`는 공백으로 구분한 커맨드 토큰입니다.
프롬프트를 특정 위치에 넣으려면 `{prompt}` 플레이스홀더를 사용하세요.

예시:

```powershell
$env:GEMINI_CMD = "gemini --prompt {prompt}"
```
