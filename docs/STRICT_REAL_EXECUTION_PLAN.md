# Strict Real-Mode Execution Plan

Date: 2026-02-26  
Goal: No mock fallback. If CLI/auth is missing, stop immediately with actionable guidance.

## Steps

1. [x] Remove automatic mock fallback from runner command resolution.
2. [x] Add runner strict preflight API with install/auth guidance.
3. [x] Block `run/codex` and `run/gemini` when readiness fails.
4. [x] Add orchestrator endpoint to expose runner preflight state.
5. [x] Block `/api/chat` before workflow queue if preflight fails.
6. [x] Add UI readiness checker and block Run button when not ready.
7. [x] Set docker/env defaults to strict real mode.
8. [x] Run docker-internal failure-path validation (missing auth -> blocked).
9. [ ] Run docker-internal success-path validation with real credentials.
10. [ ] Finalize docs/Notion logs and release checklist.

## Current Result

- Strict gate is active.
- Missing auth now returns immediate, actionable `412` errors.
- Workflow no longer runs in silent mock fallback mode.
