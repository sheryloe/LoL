# Chat-Project Roadmap

## Current Stage (2026-02-26)

1. Two parallel implementations exist.
2. `D:\AI_Vibe\orchestrator`: project-centric UI and worker execution (codex/gemini/ollama), but no chat-room workflow loop.
3. `D:\AI_Vibe\LoL\orchestrator` + `runner`: chat/workflow loop and SSE streaming exist, but no project(room) settings UI and no project-level orchestration controls.
4. Execution baseline is healthy:
5. `orchestrator` health/root respond in local smoke tests.
6. `runner` health/git status respond in local smoke tests.
7. Main gap: chat-room-as-project model is not unified yet.

## Progress Update (Current Iteration)

1. Completed item 1 (single active implementation target: `D:\AI_Vibe\LoL\orchestrator`).
2. Completed item 2 (`ProjectRoom` model with `schema_version`).
3. Completed item 3 (persistent `data/projects/<project_id>/settings.json` store).
4. Completed item 4 (settings APIs: list/create/get/put/patch).
5. Completed item 5 (project settings UI panel on the main orchestrator page).
6. Completed item 6 (`/api/chat` now resolves defaults by `project_id` settings).
7. Completed item 7 (project-level conversation event persistence + read API/UI panel).
8. Completed item 8 (workflow run state persistence + list/get API/UI panel).

## Priority Backlog (Top 20)

1. Unify codebase into one source of truth (`D:\AI_Vibe\LoL`) and stop dual-track edits.
2. Define `ProjectRoom` domain model (`project_id == room_id`) with schema versioning.
3. Add persistent project settings store (`data/projects/*.json` or sqlite).
4. Add Settings API (`GET/POST/PATCH /api/projects/.../settings`).
5. Build project settings UI page (CLI command templates, write policy, cwd, fix mode).
6. Change chat start API to accept `project_id` and resolve defaults from settings.
7. Persist conversation messages per project-room (user/assistant/system/runner events).
8. Persist workflow state machine per run (`queued/running/review/fix/completed/failed/canceled`).
9. Add fast-fail runner preflight with short timeout and clear error codes.
10. Add cancellation endpoint for long-running workflow jobs.
11. Make agent pipeline configurable per project (plan/implement/review/fix on/off and order).
12. Add role-level CLI config per project (codex cmd, gemini cmd, args templates).
13. Add artifact timeline UI (message stream + step artifacts + statuses in one view).
14. Add file diff viewer and touched-files summary per run.
15. Add guarded git action flow (status -> commit draft -> commit -> push with policy checks).
16. Add project-level permission policy (read-only / write-limited / full-write).
17. Replace static admin token with secure auth strategy and secret loading.
18. Add audit trail (who changed settings, who ran write operations, what changed).
19. Add test layers: unit, API integration, workflow e2e, failure-path tests.
20. Add ops layer: metrics, structured logs, trace IDs, health dashboards.

## Delivery Phases

1. Phase 1 (Foundation): items 1-5.
2. Phase 2 (Workflow Core): items 6-10.
3. Phase 3 (Collaboration UX): items 11-15.
4. Phase 4 (Security + Reliability): items 16-20.

## Immediate Build Order

1. Implement items 1-3.
2. Implement items 4-6.
3. Wire UI to run workflow by project-room and verify end-to-end.
4. Then proceed to items 7-10.
