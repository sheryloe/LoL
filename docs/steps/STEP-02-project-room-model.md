# Step 02 - Project Room Model

## Goal
Treat one chat room as one project context.

## What Was Implemented
Defined project-room settings model with defaults (session_id, cwd, fix mode, cmd templates, write policy).

## Expected Result
Workflow starts with stable defaults even when request omits optional fields.

## Actual Result
Chat requests resolve defaults from project settings before workflow starts.

## Verification
~~~powershell
GET /api/projects/{project_id}/settings`nPOST /api/chat with only project_id + message
~~~

## Outcome
Project-based execution context is stable and reusable.

## Next
Add per-project step pipeline toggle in later phase.

