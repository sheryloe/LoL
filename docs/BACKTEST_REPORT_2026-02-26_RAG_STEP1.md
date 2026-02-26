# Backtest Report - RAG Step 1

Date: 2026-02-26  
Scope: Project-level RAG ingest/search/context injection foundation

## Environment

- Execution policy: Docker internal only
- Orchestrator container: `lol-orchestrator`
- Runner container: `lol-runner`
- Raw evidence: [backtest_results_2026-02-26_rag_step1.json](./backtest_results_2026-02-26_rag_step1.json)

## What Was Tested

1. Project exists and orchestrator health is OK.
2. RAG document ingest works for:
   - inline text source
   - repository file source (`README.md`)
3. RAG document listing returns stored metadata (`document_id`, source, chunk count).
4. RAG search returns ranked hits and generated context preview.
5. Chat request with `include_rag=true` writes RAG usage signals into conversation logs.

## Result Summary

- Pass: `GET /health`
- Pass: `POST /api/projects/{project_id}/rag/documents` (text + file)
- Pass: `GET /api/projects/{project_id}/rag/documents`
- Pass: `POST /api/projects/{project_id}/rag/search`
- Pass: `POST /api/chat` accepts RAG parameters and queues workflow
- Pass: Conversation stores `rag_hit_count` and `source=rag` `context_attached` events
- Known external dependency failure: workflow run failed at Gemini API network/auth phase (expected in current environment)

## Key Observation

RAG Step 1 path is operational independent of final model execution success.  
Even when model execution fails later, ingest/search/context-attachment behavior is persisted and traceable.

## Next

Step 2 should implement retrieval quality controls:

1. Source weighting (project docs > conversation snippets).
2. Chunk-level deduplication and stronger ranking rules.
3. Prompt budget controls and quote-citation formatting.
