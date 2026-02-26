# Step 06 - Chat Request Resolution

## Goal
Resolve session/cwd/fix defaults from project settings at chat start.

## What Was Implemented
POST /api/chat maps request -> ResolvedChatRequest using project defaults.

## Expected Result
Users send only message + project_id for normal flow.

## Actual Result
Resolved request is persisted with project/session context before queueing workflow.

## Verification
~~~powershell
POST /api/chat and inspect conversation entry fields
~~~

## Outcome
Chat start now behaves as project-aware orchestration.

## Next
Add request-level overrides visibility in UI timeline.

