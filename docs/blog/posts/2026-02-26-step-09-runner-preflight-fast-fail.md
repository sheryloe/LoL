---
title: "Step 09 - Runner Preflight Fast-Fail"
date: "2026-02-26"
category: "coworker-chat-tool"
tags: ["orchestrator", "runner", "codex", "gemini", "workflow"]
---

## Why This Step
Fail quickly when runner connectivity is broken.

## Implementation Notes
Workflow preflight checks runner /health and /git/status with short timeout before agent steps.

## Expected vs Actual
- Expected: No long-hanging runs when runner is unreachable.
- Actual: Current smoke run failed fast with RUNNER_PREFLIGHT_FAILED: All connection attempts failed and status=failed.

## Test
~~~powershell
POST /api/chat then GET /api/workflow/{id} while runner route is unreachable from container
~~~

## Result
Fail-fast behavior works; environment routing still needs fixing on some desktop setups.

## Next Step
Stabilize host.docker.internal routing in Rancher Desktop environments.

