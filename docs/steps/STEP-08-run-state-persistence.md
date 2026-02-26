# Step 08 - Workflow Run State Persistence

## Goal
Persist workflow status and artifacts per run.

## What Was Implemented
Saved run snapshots in data/projects/<project_id>/runs/<workflow_job_id>.json.

## Expected Result
Run list/detail survives refresh and restart.

## Actual Result
Run history API returns status transitions and artifact metadata.

## Verification
~~~powershell
GET /api/projects/{project_id}/runs`nGET /api/projects/{project_id}/runs/{workflow_job_id}
~~~

## Outcome
Run observability exists at project level.

## Next
Add diff-centric run comparison view.

