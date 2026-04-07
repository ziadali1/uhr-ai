---
phase: 04-hybrid-search-index
plan: 05
subsystem: rag-retrieval
tags: [hybrid-search, embeddings, pgvector, retriever, tdd]
dependency_graph:
  requires: [04-02, 04-03]
  provides: [RETRIEVE-03]
  affects: [backend/services/rag/retriever.py]
tech_stack:
  added: []
  patterns: [query-embedding-before-search, graceful-degradation, query_vector-passthrough]
key_files:
  modified:
    - backend/services/rag/retriever.py
    - backend/tests/rag/test_retriever.py
decisions:
  - "query_vector always passed to search() — None triggers fts_search fallback, non-None triggers hybrid_search RPC"
  - "generate_embedding imported at module level in retriever.py — enables clean mock patching in tests"
  - "Wave 0 skip stubs replaced entirely with 3 real tests covering embedding call, vector passthrough, and graceful degradation"
metrics:
  duration: 68s
  completed_date: "2026-04-07"
  tasks_completed: 1
  files_modified: 2
---

# Phase 04 Plan 05: Retriever Query Embedding Summary

**One-liner:** Retriever now calls `generate_embedding(question)` before `search()`, passing `query_vector` to enable Supabase `hybrid_search` RPC (pgvector + RRF) with graceful degradation to `fts_search` when embedding returns None.

## What Was Built

Updated `backend/services/rag/retriever.py` to embed the user's query before calling `search()`. Only 3 lines changed — the rest of the retriever (SYSTEM_PROMPT, context assembly, source tracking, return value) is completely unchanged.

**Changes to retriever.py:**
1. Added `from services.azure.embeddings import generate_embedding` import
2. Added `query_vector = generate_embedding(question)` before the search call
3. Updated `search()` call to pass `query_vector=query_vector`

The `search()` function (Plan 02) already handles routing: with `query_vector` → Supabase `hybrid_search` RPC (pgvector + RRF); without → `fts_search` RPC; mock mode → in-memory BM25 regardless.

## TDD Execution

**RED phase:** Replaced Wave 0 `@pytest.mark.skip` stubs with 3 real failing tests.

**GREEN phase:** Added import + 2-line change to retriever.py. All 3 tests pass.

**Tests written:**
- `test_build_context_prompt_calls_generate_embedding` — asserts `generate_embedding` called with query text
- `test_build_context_prompt_passes_vector_to_search` — asserts `search()` receives the generated vector
- `test_retriever_degrades_when_embedding_fails` — asserts `search()` called with `query_vector=None` when embedding fails

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all data flows are wired. Mock mode uses `_mock_search` (in-memory BM25) per D-23/D-24, which is correct behavior.

## Self-Check: PASSED
