---
title: "Step 03 - Persistent Settings Store"
date: "2026-02-26"
category: "coworker-chat-tool"
tags: ["orchestrator", "runner", "codex", "gemini", "workflow"]
---

## Why This Step
Persist per-project operating rules.

## Implementation Notes
Stored settings in data/projects/<project_id>/settings.json and loaded through store layer.

## Expected vs Actual
- Expected: Restart-safe settings and deterministic runtime behavior.
- Actual: Settings survive orchestrator restarts via mounted data volume.

## Test
~~~powershell
Create project -> edit settings -> restart orchestrator -> read settings again
~~~

## Result
Settings persistence works as designed.

## Next Step
Add schema migration for future model changes.

