# Step 07 - Conversation Persistence

## Goal
Keep project-level event history for collaboration traceability.

## What Was Implemented
Persisted user/system/workflow events to data/projects/<project_id>/conversation.ndjson.

## Expected Result
Anyone can reconstruct what happened in a room.

## Actual Result
Conversation API returns ordered history with source/session/workflow identifiers.

## Verification
~~~powershell
GET /api/projects/{project_id}/conversation?limit=200
~~~

## Outcome
Traceable room history is available for handoff/debug.

## Next
Add search/filter by workflow_job_id and source.

