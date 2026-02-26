from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.config import CLI_AUTH_TIMEOUT_SECONDS, CODEX_CLI_BIN, DOCKER_CONTAINER_NAME, GEMINI_CLI_BIN


@dataclass
class AgentAuthStatus:
    agent: str
    cli_bin: str
    installed: bool
    authenticated: bool
    method: str
    detail: str
    login_command: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent": self.agent,
            "cli_bin": self.cli_bin,
            "installed": self.installed,
            "authenticated": self.authenticated,
            "method": self.method,
            "detail": self.detail,
            "login_command": self.login_command,
        }


class CliAuthService:
    def _clean_codex_status(self, text: str) -> str:
        lines = [line.rstrip() for line in (text or "").splitlines()]
        filtered = [line for line in lines if line and not line.lower().startswith("warning: proceeding")]
        return "\n".join(filtered).strip()

    def _is_installed(self, cli_bin: str) -> bool:
        return shutil.which(cli_bin) is not None

    def _codex_login_command(self) -> str:
        return f"docker exec -it {DOCKER_CONTAINER_NAME} codex login --device-auth"

    def _gemini_login_command(self) -> str:
        return f"docker exec -it {DOCKER_CONTAINER_NAME} gemini  # then type /auth"

    def codex_status(self) -> AgentAuthStatus:
        login_command = self._codex_login_command()
        installed = self._is_installed(CODEX_CLI_BIN)
        if not installed:
            return AgentAuthStatus(
                agent="codex",
                cli_bin=CODEX_CLI_BIN,
                installed=False,
                authenticated=False,
                method="missing",
                detail=f"{CODEX_CLI_BIN} binary not found in container PATH",
                login_command=login_command,
            )

        try:
            proc = subprocess.run(
                [CODEX_CLI_BIN, "login", "status"],
                capture_output=True,
                text=True,
                timeout=CLI_AUTH_TIMEOUT_SECONDS,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return AgentAuthStatus(
                agent="codex",
                cli_bin=CODEX_CLI_BIN,
                installed=True,
                authenticated=False,
                method="unknown",
                detail=f"codex login status timed out ({CLI_AUTH_TIMEOUT_SECONDS}s)",
                login_command=login_command,
            )
        except Exception as exc:  # noqa: BLE001
            return AgentAuthStatus(
                agent="codex",
                cli_bin=CODEX_CLI_BIN,
                installed=True,
                authenticated=False,
                method="unknown",
                detail=f"codex login status failed: {exc}",
                login_command=login_command,
            )

        output = self._clean_codex_status((proc.stdout or proc.stderr or "").strip())
        if proc.returncode == 0:
            return AgentAuthStatus(
                agent="codex",
                cli_bin=CODEX_CLI_BIN,
                installed=True,
                authenticated=True,
                method="cli-login",
                detail=output or "logged in",
                login_command=login_command,
            )
        return AgentAuthStatus(
            agent="codex",
            cli_bin=CODEX_CLI_BIN,
            installed=True,
            authenticated=False,
            method="none",
            detail=output or "not logged in",
            login_command=login_command,
        )

    def _load_gemini_settings(self) -> tuple[dict[str, Any] | None, str | None]:
        candidate_paths = (
            Path.home() / ".gemini" / "settings.json",
            Path.home() / ".config" / "gemini" / "settings.json",
        )
        for path in candidate_paths:
            if not path.exists():
                continue
            try:
                raw = path.read_text(encoding="utf-8")
                payload = json.loads(raw)
            except Exception:
                return None, str(path)
            if isinstance(payload, dict):
                return payload, str(path)
        return None, None

    def _pick_nested(self, source: dict[str, Any], path: tuple[str, ...]) -> Any:
        node: Any = source
        for key in path:
            if not isinstance(node, dict):
                return None
            node = node.get(key)
        return node

    def _gemini_auth_type(self, settings: dict[str, Any]) -> str:
        candidates = (
            ("security", "auth", "selectedType"),
            ("selectedAuthType",),
            ("authType",),
            ("authMethod",),
            ("auth_type",),
            ("auth_method",),
        )
        for path in candidates:
            value = self._pick_nested(settings, path)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return ""

    def gemini_status(self) -> AgentAuthStatus:
        login_command = self._gemini_login_command()
        installed = self._is_installed(GEMINI_CLI_BIN)
        if not installed:
            return AgentAuthStatus(
                agent="gemini",
                cli_bin=GEMINI_CLI_BIN,
                installed=False,
                authenticated=False,
                method="missing",
                detail=f"{GEMINI_CLI_BIN} binary not found in container PATH",
                login_command=login_command,
            )

        settings, settings_path = self._load_gemini_settings()
        if settings is None:
            detail = "settings.json not found" if settings_path is None else f"settings unreadable: {settings_path}"
            return AgentAuthStatus(
                agent="gemini",
                cli_bin=GEMINI_CLI_BIN,
                installed=True,
                authenticated=False,
                method="none",
                detail=detail,
                login_command=login_command,
            )

        auth_type = self._gemini_auth_type(settings)
        if not auth_type:
            return AgentAuthStatus(
                agent="gemini",
                cli_bin=GEMINI_CLI_BIN,
                installed=True,
                authenticated=False,
                method="none",
                detail=f"auth type not configured in {settings_path}",
                login_command=login_command,
            )

        normalized = auth_type.lower().strip()
        if normalized == "oauth-personal":
            return AgentAuthStatus(
                agent="gemini",
                cli_bin=GEMINI_CLI_BIN,
                installed=True,
                authenticated=True,
                method=normalized,
                detail=f"auth={auth_type} ({settings_path})",
                login_command=login_command,
            )

        return AgentAuthStatus(
            agent="gemini",
            cli_bin=GEMINI_CLI_BIN,
            installed=True,
            authenticated=False,
            method=normalized,
            detail=(
                f"auth={auth_type} in {settings_path}; "
                "expected oauth-personal (CLI login session)"
            ),
            login_command=login_command,
        )

    def get_status(self, worker_name: str) -> AgentAuthStatus:
        worker = worker_name.strip().lower()
        if worker == "codex":
            return self.codex_status()
        if worker == "gemini":
            return self.gemini_status()
        raise ValueError(f"auth status is only available for codex/gemini: {worker_name}")

    def summary(self) -> dict[str, Any]:
        codex = self.codex_status()
        gemini = self.gemini_status()
        return {
            "codex": codex.to_dict(),
            "gemini": gemini.to_dict(),
        }

    def ensure_ready(self, worker_name: str) -> None:
        status = self.get_status(worker_name)
        if not status.installed:
            raise RuntimeError(f"{status.agent} CLI is not installed: {status.detail}")
        if not status.authenticated:
            raise RuntimeError(
                f"{status.agent} CLI login is required ({status.detail}). "
                f"Run: {status.login_command}"
            )


cli_auth_service = CliAuthService()
