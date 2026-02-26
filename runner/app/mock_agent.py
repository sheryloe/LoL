from __future__ import annotations

import sys


def _read_prompt(args: list[str]) -> str:
    if args:
        return " ".join(args).strip()
    data = sys.stdin.read().strip()
    return data


def run_codex(prompt: str) -> None:
    print("# Summary")
    print("Mock Codex executed successfully.")
    print()
    print("# Patch")
    print("No code changes were applied in mock mode.")
    print()
    print("# Files")
    print("none")
    print()
    if prompt:
        print("## Prompt Echo")
        print(prompt[:4000])


def run_gemini(prompt: str) -> None:
    print("VERDICT: PASS")
    print()
    print("# Plan")
    print("- Parse request")
    print("- Produce actionable steps")
    print()
    print("# Tasks")
    print("- Provide implementation guidance")
    print()
    print("# Review")
    print("Mock review passed.")
    print()
    print("# Risks")
    print("- Real CLI/auth not enabled; this is mock output.")
    print()
    print("# Suggested Fix")
    print("- Configure CODEX_CMD/GEMINI_CMD for real CLI execution.")
    print()
    if prompt:
        print("## Prompt Echo")
        print(prompt[:4000])


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: python -m app.mock_agent <codex|gemini> [prompt...]")
        return 2

    role = sys.argv[1].strip().lower()
    prompt = _read_prompt(sys.argv[2:])

    if role == "codex":
        run_codex(prompt)
        return 0
    if role == "gemini":
        run_gemini(prompt)
        return 0

    print(f"unknown role: {role}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
