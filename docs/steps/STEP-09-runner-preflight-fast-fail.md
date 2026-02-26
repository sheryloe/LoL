# Step 09 - Runner Preflight Fast-Fail

## Goal
Fail quickly when runner connectivity is broken.

## What Was Implemented
Workflow preflight checks runner /health and /git/status with short timeout before agent steps.

## Expected Result
No long-hanging runs when runner is unreachable.

## Actual Result
Current smoke run failed fast with RUNNER_PREFLIGHT_FAILED: All connection attempts failed and status=failed.

## Verification
~~~powershell
POST /api/chat then GET /api/workflow/{id} while runner route is unreachable from container
~~~

## Outcome
Fail-fast behavior works; environment routing still needs fixing on some desktop setups.

## Next
Stabilize host.docker.internal routing in Rancher Desktop environments.

