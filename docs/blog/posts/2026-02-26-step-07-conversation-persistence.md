---
title: "Step 07 - Conversation Persistence"
date: "2026-02-26"
category: "coworker-chat-tool"
tags: ["orchestrator", "runner", "codex", "gemini", "workflow"]
---

## Why This Step
Keep project-level event history for collaboration traceability.

## Implementation Notes
Persisted user/system/workflow events to data/projects/<project_id>/conversation.ndjson.

## Expected vs Actual
- Expected: Anyone can reconstruct what happened in a room.
- Actual: Conversation API returns ordered history with source/session/workflow identifiers.

## Test
~~~powershell
GET /api/projects/{project_id}/conversation?limit=200
~~~

## Result
Traceable room history is available for handoff/debug.

## Next Step
Add search/filter by workflow_job_id and source.

