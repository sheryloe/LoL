# TODO Roadmap (Priority)

Last update: 2026-02-26

## P0 (Immediate)

1. Stabilize orchestrator -> runner connectivity on desktop container runtimes.
2. Add automated tests for preflight fail-fast behavior.
3. Add automated tests for workflow cancel invariant (no further step after cancel).
4. Improve UI error copy with actionable diagnosis when runner link fails.

## P1 (Near-term)

1. Step 11: Per-project pipeline composition (on/off + step order).
2. Step 12: Per-project CLI template/args policy.
3. Step 13: Unified timeline UX for events + artifacts + status.
4. Step 14: Run diff and changed-file summary view.
5. Step 15: Guarded git operation flow.

## P2 (Mid-term)

1. Step 16: Permission tiers.
2. Step 17: Auth and secret management upgrade.
3. Step 18: Audit trail schema + API + UI.
4. Step 19: Full automated test pyramid.
5. Step 20: Metrics/logging/trace observability.

## Done (Step 01-10)

1. Single source repo lock.
2. Project room model.
3. Settings persistence.
4. Settings APIs.
5. Settings UI panel.
6. Chat request default resolution.
7. Conversation persistence.
8. Run state persistence.
9. Preflight fail-fast gate.
10. Workflow cancel control.
