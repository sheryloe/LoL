import os
from pathlib import Path

APP_NAME = "Web Orchestrator v1"
APP_VERSION = "0.1.0"

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
PROJECTS_ROOT = DATA_DIR / "projects"

TREND_DAILY_LIMIT = 20
WRITE_ENABLED_DEFAULT = False
UI_ADMIN_TOKEN = "change-me"
OLLAMA_BASE_URL = "http://localhost:11434"

OLLAMA_MODEL = "qwen2.5:7b-instruct"
CODEX_CLI_BIN = "codex"
GEMINI_CLI_BIN = "gemini"
CODEX_CLI_CMD = os.getenv("CODEX_CLI_CMD", "codex exec --skip-git-repo-check --full-auto {prompt}")
GEMINI_CLI_CMD = os.getenv("GEMINI_CLI_CMD", "gemini --prompt {prompt} --yolo")
SUBPROCESS_TIMEOUT_SECONDS = 120
BAD_REQUEST_RETRY_COUNT = 2
BAD_REQUEST_RETRY_DELAY_SECONDS = 1.0
CLI_AUTH_TIMEOUT_SECONDS = int(os.getenv("CLI_AUTH_TIMEOUT_SECONDS", "8"))
DOCKER_CONTAINER_NAME = os.getenv("DOCKER_CONTAINER_NAME", "web-orchestrator-v1")

NOTION_API_BASE_URL = "https://api.notion.com/v1"
NOTION_API_VERSION = "2022-06-28"
NOTION_TIMEOUT_SECONDS = 30
NOTION_TOKEN = os.getenv("NOTION_TOKEN", "")
NOTION_PARENT_PAGE_ID = os.getenv("NOTION_PARENT_PAGE_ID", "")
