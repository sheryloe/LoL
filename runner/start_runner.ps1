$ErrorActionPreference = "Stop"

if (-not (Test-Path ".venv")) {
    py -m venv .venv
}

. .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt

if (-not $env:RUNNER_ROOT_DIR) {
    $env:RUNNER_ROOT_DIR = "D:\AI_Vibe\LoL"
}
if (-not $env:RUNNER_WRITE_ENABLED) {
    $env:RUNNER_WRITE_ENABLED = "false"
}
if (-not $env:CODEX_CMD) {
    $env:CODEX_CMD = "codex"
}
if (-not $env:GEMINI_CMD) {
    $env:GEMINI_CMD = "gemini"
}

uvicorn app.main:app --host 0.0.0.0 --port 8765 --reload
