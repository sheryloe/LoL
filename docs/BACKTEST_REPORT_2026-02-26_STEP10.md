# Backtest Report - Step 10 Smoke Validation

- Generated: 2026-02-26T13:37:53+09:00
- Project ID: room_step10_20260226133745
- Total: 8
- Passed: 8
- Failed: 0

## Result Table

| Test | Status | Detail |
| --- | --- | --- |
| runner_health | PASS | {"status":"ok","root_dir":"D:\\AI_Vibe\\LoL","write_enabled":"False"} |
| orchestrator_health | PASS | {"status":"ok","runner_base_url":"http://host.docker.internal:8765","root_dir":"/workspace/LoL","journal_dir":"/app/data/journals","projects_dir":"/app/data/projects"} |
| create_project | PASS | {"schema_version":1,"project_id":"room_step10_20260226133745","title":"Step10 Validation Room","default_session_id":"room_step10_20260226133745","default_cwd_relative":".","default... |
| put_settings | PASS | {"schema_version":1,"project_id":"room_step10_20260226133745","title":"Step10 Validation Room","default_session_id":"room_step10_20260226133745","default_cwd_relative":".","default... |
| start_chat_workflow | PASS | {"project_id":"room_step10_20260226133745","workflow_job_id":"17985b09-2909-4b52-92e9-b42cd051022a","session_id":"room_step10_20260226133745","status":"queued"} |
| get_workflow | PASS | {"workflow_job_id":"17985b09-2909-4b52-92e9-b42cd051022a","project_id":"room_step10_20260226133745","session_id":"room_step10_20260226133745","status":"failed","cwd_relative":".","... |
| list_runs | PASS | {"project_id":"room_step10_20260226133745","items":[{"workflow_job_id":"17985b09-2909-4b52-92e9-b42cd051022a","project_id":"room_step10_20260226133745","session_id":"room_step10_20... |
| conversation_log | PASS | {"project_id":"room_step10_20260226133745","items":[{"timestamp":"2026-02-26T04:37:47.904075+00:00","source":"user_message","project_id":"room_step10_20260226133745","session_id":"... |

## Notes

1. API-level smoke checks passed for project creation/settings/workflow start/run listing/conversation history.
2. Workflow execution failed fast at preflight in this environment, which is expected behavior for broken runner route from container context.
3. Next action is runtime routing hardening for host.docker.internal on the local container runtime.
