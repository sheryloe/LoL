---
title: "Step 02 - Project Room Model"
date: "2026-02-26"
category: "coworker-chat-tool"
tags: ["orchestrator", "runner", "codex", "gemini", "workflow"]
---

## Why This Step
Treat one chat room as one project context.

## Implementation Notes
Defined project-room settings model with defaults (session_id, cwd, fix mode, cmd templates, write policy).

## Expected vs Actual
- Expected: Workflow starts with stable defaults even when request omits optional fields.
- Actual: Chat requests resolve defaults from project settings before workflow starts.

## Test
~~~powershell
GET /api/projects/{project_id}/settings`nPOST /api/chat with only project_id + message
~~~

## Result
Project-based execution context is stable and reusable.

## Next Step
Add per-project step pipeline toggle in later phase.

