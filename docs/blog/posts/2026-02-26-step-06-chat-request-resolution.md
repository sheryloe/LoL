---
title: "Step 06 - Chat Request Resolution"
date: "2026-02-26"
category: "coworker-chat-tool"
tags: ["orchestrator", "runner", "codex", "gemini", "workflow"]
---

## Why This Step
Resolve session/cwd/fix defaults from project settings at chat start.

## Implementation Notes
POST /api/chat maps request -> ResolvedChatRequest using project defaults.

## Expected vs Actual
- Expected: Users send only message + project_id for normal flow.
- Actual: Resolved request is persisted with project/session context before queueing workflow.

## Test
~~~powershell
POST /api/chat and inspect conversation entry fields
~~~

## Result
Chat start now behaves as project-aware orchestration.

## Next Step
Add request-level overrides visibility in UI timeline.

