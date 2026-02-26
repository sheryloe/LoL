from __future__ import annotations

import shlex
from typing import Iterable


def build_cli_command(
    cli_bin: str,
    prompt: str,
    cli_args: Iterable[str],
    default_template: str,
) -> tuple[list[str], bool]:
    """
    Returns (command, use_stdin_prompt).
    """
    args = [str(arg) for arg in cli_args]
    if args:
        has_placeholder = any("{prompt}" in arg for arg in args)
        resolved = [arg.replace("{prompt}", prompt) for arg in args]
        return [cli_bin, *resolved], not has_placeholder

    template = (default_template or "").strip()
    if not template:
        return [cli_bin, prompt], False

    parts = shlex.split(template)
    if not parts:
        return [cli_bin, prompt], False

    resolved: list[str] = []
    has_placeholder = False
    for token in parts:
        if "{prompt}" in token:
            has_placeholder = True
            resolved.append(token.replace("{prompt}", prompt))
        else:
            resolved.append(token)
    if not has_placeholder:
        resolved.append(prompt)
    return resolved, False
