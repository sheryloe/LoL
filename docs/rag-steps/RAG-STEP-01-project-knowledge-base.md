# RAG Step 01 - Project Knowledge Base Foundation

## Goal

Create a real, usable RAG baseline so each chat room (project) can keep reusable knowledge and attach retrieval context during workflow execution.

## Why This Step

The current co-worker model (Codex + Gemini pipeline) had project memory in logs, but no retrieval layer.
Without RAG, repeated implementation sessions lose continuity unless users manually re-paste context each time.

## Implementation

### 1) Data Model and API Contracts

Added RAG request schemas:

- `RagIngestRequest`
- `RagSearchRequest`
- Extended `ChatRequest`:
  - `include_rag`
  - `rag_top_k`
  - `rag_max_chars`

File:
- [models.py](/d:/AI_Vibe/LoL/orchestrator/app/models.py)

### 2) Project-Level RAG Store

Added `ProjectRagStore` with:

- Project-scoped index file: `rag_index.json`
- Text chunking with overlap
- Tokenization + term-frequency scoring
- Search result ranking + context preview builder
- Ingest from inline text or repository file path

File:
- [rag_store.py](/d:/AI_Vibe/LoL/orchestrator/app/rag_store.py)

### 3) Orchestrator API Endpoints

Added endpoints:

- `GET /api/projects/{project_id}/rag/documents`
- `POST /api/projects/{project_id}/rag/documents`
- `POST /api/projects/{project_id}/rag/search`

And chat integration:

- If `include_rag=true`, top retrieval context is prepended to the model prompt.
- Conversation log now records:
  - `rag_hit_count` on `user_message`
  - `source=rag`, `event=context_attached` event with hit metadata

File:
- [main.py](/d:/AI_Vibe/LoL/orchestrator/app/main.py)

### 4) UI Integration

Added RAG panel to web UI:

- Document ingest (text or file path)
- Tag input
- Search preview
- Document list
- Toggle for workflow RAG injection + `top_k`

File:
- [index.html](/d:/AI_Vibe/LoL/orchestrator/app/static/index.html)

## Expected Result

1. User can ingest project docs and files into RAG index.
2. User can search relevant context before running workflow.
3. Workflow chat request can reuse project context automatically.
4. Retrieval usage remains auditable in project conversation logs.

## Actual Result

All target APIs and UI controls are connected and functional.
RAG ingest/search/context-attachment completed successfully in Docker internal verification.

## Test Evidence

Backtest report:
- [BACKTEST_REPORT_2026-02-26_RAG_STEP1.md](/d:/AI_Vibe/LoL/docs/BACKTEST_REPORT_2026-02-26_RAG_STEP1.md)

Raw result:
- [backtest_results_2026-02-26_rag_step1.json](/d:/AI_Vibe/LoL/docs/backtest_results_2026-02-26_rag_step1.json)

## Example Calls

```http
POST /api/projects/rag-step1-room/rag/documents
Content-Type: application/json

{
  "source_type": "text",
  "title": "Step1 acceptance criteria",
  "content": "A chat room is a project. Step1 requires project-level RAG ingestion.",
  "tags": ["rag", "step1"]
}
```

```http
POST /api/projects/rag-step1-room/rag/search
Content-Type: application/json

{
  "query": "step1 rag context injection",
  "top_k": 5,
  "max_chars": 1200
}
```

```http
POST /api/chat
Content-Type: application/json

{
  "project_id": "rag-step1-room",
  "session_id": "rag-step1-room",
  "message": "Suggest next three priorities.",
  "cwd_relative": ".",
  "include_rag": true,
  "rag_top_k": 4
}
```

## What We Learned

1. RAG path can be validated independently from final model execution success.
2. Conversation log annotations are critical for traceability and future debugging.
3. The first practical bottleneck after RAG is retrieval quality tuning, not storage.

## Next Step (RAG-STEP-02)

Improve retrieval quality and trust:

1. Add source weighting rules.
2. Add chunk deduplication and token budget heuristics.
3. Add quote/citation formatting for attached context.
