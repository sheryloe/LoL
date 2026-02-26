---
title: "Step 10 - Workflow Cancel and Operator Controls"
date: "2026-02-26"
category: "coworker-chat-tool"
tags: ["orchestrator", "runner", "codex", "gemini", "workflow"]
---

## Why This Step
Allow operator to stop in-flight workflows safely.

## Implementation Notes
Added cancel endpoint and UI control for active workflow job.

## Expected vs Actual
- Expected: Canceled runs stop further step execution and emit canceled status.
- Actual: Cancel API is exposed and integrated in UI; full cancellation path depends on runner reachability.

## Test
~~~powershell
POST /api/workflow/{workflow_job_id}/cancel during running job
~~~

## Result
Operational control plane is in place for long-running workflows.

## Next Step
Add explicit post-cancel invariant tests (no extra steps after cancel).

