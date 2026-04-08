---
phase: 05-query-routing-and-context-assembly
plan: "05"
subsystem: rag/testing
tags: [testing, router, retriever, tdd, RETRIEVE-04, RETRIEVE-05]
dependency_graph:
  requires: [05-04]
  provides: [RETRIEVE-04-validated, RETRIEVE-05-validated]
  affects: [backend/tests/rag/test_router.py, backend/tests/rag/test_retriever.py]
tech_stack:
  added: []
  patterns: [unittest.mock.patch, MagicMock chaining, patch.dict os.environ, RoutingResult mock injection]
key_files:
  created: []
  modified:
    - backend/tests/rag/test_router.py
    - backend/tests/rag/test_retriever.py
decisions:
  - "patch _use_mock_cache to None before each mock-mode test so _use_mock() re-reads env var (cache invalidation)"
  - "test_sql_user_isolation uses select_mock.eq.call_args_list to inspect first .eq() call in chain — method_calls on mock_client only shows top-level calls"
  - "test_context_includes_sql_section patches retriever module functions directly (services.rag.retriever.route_query) not router — retriever imports are the reference target"
metrics:
  duration: 5min
  completed: 2026-04-08T10:51:54Z
  tasks_completed: 2
  files_modified: 2
---

# Phase 05 Plan 05: Wave 3 Test Implementation Summary

All 12 Wave 0 test stubs (11 in test_router.py + 1 in test_retriever.py) unskipped and implemented. Full rag test suite passes green.

## Tasks Completed

### Task 1: Implement all 11 test bodies in test_router.py
**Commit:** 9089ec9

Replaced 11 `@pytest.mark.skip` stubs with full implementations:

- `test_expand_abbreviations` — asserts HbA1c->hemoglobina glicada, PA->pressão arterial expansion
- `test_route_mock_mode` — verifies generate_json not called in mock mode, returns search_only
- `test_route_narrative_returns_search_only` — mocked LLM returns search_only with entity extraction
- `test_route_aggregation_returns_sql_only` — mocked LLM returns sql_only with date-ranged sql_step
- `test_route_mixed_intent` — mocked LLM returns mixed with both sql_steps and search_queries
- `test_route_fallback_on_llm_failure` — generate_json raises Exception, result degrades to search_only
- `test_route_returns_routing_result_model` — structural assertion on RoutingResult model shape
- `test_sql_observations_scoped_by_user_id` — Supabase mock chain returns 1 row for observations step
- `test_sql_user_isolation` — verifies .eq("user_id", "user-A") called on select chain (not LLM-provided)
- `test_chat_block_structured_lab` — StructuredResult with StructuredLab asserts HbA1c, 7.8, [high], Summary
- `test_chat_block_fallback` — _fetch_structured_result=None uses raw excerpt, within 1200 char budget

All 11 pass. Zero skipped. Zero failed.

### Task 2: Implement test_context_includes_sql_section in test_retriever.py
**Commit:** 45785b4

Removed `@pytest.mark.skip` from `test_context_includes_sql_section`. Implemented full body:
- Patches `services.rag.retriever.route_query` to return sql_only RoutingResult
- Patches `execute_sql_steps` returning medication row
- Patches `format_sql_block` returning block with "DADOS ESTRUTURADOS DO PACIENTE" header
- Asserts SQL section and Metformina data present in assembled system_prompt
- All 3 original retriever tests still pass

## Test Results

```
tests/rag/test_context_block.py   7 passed
tests/rag/test_embeddings.py      3 passed
tests/rag/test_indexer.py         3 passed
tests/rag/test_retriever.py       4 passed  (was 3 passed + 1 skipped)
tests/rag/test_router.py         11 passed  (was 0 passed + 11 skipped)
tests/rag/test_search_schema.py   5 skipped (Wave 0 search schema stubs — unrelated)

Total: 28 passed, 5 skipped, 0 failed
Full suite (tests/): 86 passed, 5 skipped, 0 failed
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] test_sql_user_isolation mock introspection**
- **Found during:** Task 1
- **Issue:** `str(mock_client.method_calls)` only captures top-level calls (`.table()`), not chained calls like `.select().eq("user_id", ...)`. The assertion `"user_id" in all_calls` failed.
- **Fix:** Captured `select_mock = mock_client.table.return_value.select.return_value` and inspected `select_mock.eq.call_args_list` to verify the first `.eq()` call used `("user_id", "user-A")`.
- **Files modified:** backend/tests/rag/test_router.py
- **Commit:** 9089ec9 (fixed inline before commit)

## Known Stubs

None — all test bodies are fully implemented with assertions. No placeholder text or TODO items remain in the modified files.

## Self-Check

Verified files exist:
- backend/tests/rag/test_router.py — FOUND
- backend/tests/rag/test_retriever.py — FOUND

Verified commits exist:
- 9089ec9 — test(05-05): implement all 11 router test stubs
- 45785b4 — test(05-05): implement test_context_includes_sql_section

## Self-Check: PASSED
