---
phase: 05-query-routing-and-context-assembly
plan: "04"
subsystem: rag-retriever
tags: [rag, retriever, router, context-assembly, sql, hybrid-search]
requirements: [RETRIEVE-04, RETRIEVE-05]

dependency_graph:
  requires:
    - "05-02: route_query, execute_sql_steps, format_sql_block in router.py"
    - "05-03: assemble_chat_block in router.py"
  provides:
    - "build_context_prompt() wires router into chat pipeline"
    - "SQL + search context merged into unified Claude prompt"
  affects:
    - "api/chat.py (unchanged — signature preserved)"
    - "services/rag/retriever.py (full rewrite)"

tech_stack:
  added: []
  patterns:
    - "Intent-driven retrieval: route first, then SQL and/or search"
    - "D-12/D-13 context ordering: SQL structured block before document block"
    - "D-14 top_k budget reduction: 3->2 when sql_block non-empty"
    - "D-18/D-19 SYSTEM_PROMPT: structured data as ground truth, docs as supporting evidence"

key_files:
  created: []
  modified:
    - backend/services/rag/retriever.py
    - backend/tests/rag/test_retriever.py

decisions:
  - "Route query before retrieval: route_query() is called first before any embedding or SQL"
  - "Signature preserved: build_context_prompt(question, user_id) -> tuple[str, list[str]] unchanged — api/chat.py requires zero changes"
  - "sql_only sources fallback: when no search results, sources=['dados estruturados do paciente']"
  - "assemble_chat_block with collection_date=None: SearchResult lacks collection_date; assembler handles gracefully with 'data desconhecida'"
  - "Tests updated to mock route_query: old tests patched generate_embedding + search but not route_query, causing failures due to abbreviation expansion in route_query path"

metrics:
  duration: "8min"
  completed: "2026-04-08"
  tasks_completed: 1
  files_modified: 2
---

# Phase 05 Plan 04: Retriever Router Wiring Summary

**One-liner:** Refactored `build_context_prompt()` to route via `route_query()` before retrieval, merging SQL structured blocks and search document blocks into D-12/D-13-ordered Claude context with updated D-18/D-19 SYSTEM_PROMPT.

## What Was Built

`backend/services/rag/retriever.py` was completely rewritten to replace the flat BM25+excerpt pipeline with a router-driven orchestration:

1. **`route_query(question, user_id)`** — classifies intent as `sql_only`, `search_only`, or `mixed` before any search or SQL
2. **`execute_sql_steps()` + `format_sql_block()`** — for `sql_only`/`mixed` intents, queries patient tables and formats as `=== DADOS ESTRUTURADOS DO PACIENTE ===` block
3. **`assemble_chat_block()`** — formats each search result as a structured clinical block (replaces raw `[Fonte: X]\n{excerpt}`)
4. **D-12/D-13 ordering** — SQL block appears first in context, document block second
5. **D-14 top_k budget** — reduces from 3 to 2 when sql_block is non-empty
6. **D-18/D-19 SYSTEM_PROMPT** — updated with structured data ground truth instruction and synthesis directive

The `build_context_prompt(question: str, user_id: str) -> tuple[str, list[str]]` signature is preserved exactly — `api/chat.py` required zero changes.

## Test Results

- **3 passed, 1 skipped, 0 failed** (retriever tests)
- **16 passed, 17 skipped, 0 failed** (full RAG test suite)
- Smoke test confirmed: `build_context_prompt` returns `(str, list)` correctly

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Missing assemble_chat_block in router.py**
- **Found during:** Task 1 setup
- **Issue:** The plan's dependency 05-03 feat commit (`52e9da8` — `assemble_chat_block` implementation) was in a separate worktree branch but NOT merged to main. The router.py on main was missing `assemble_chat_block`, `_fetch_structured_result`, and related model imports.
- **Fix:** Cherry-picked commit `52e9da8` from `worktree-agent-a93d2eda` to make the dependency available before implementing 05-04.
- **Files modified:** `backend/services/rag/router.py`
- **Commit:** `2137ba4`

**2. [Rule 1 - Bug] Test mocking insufficient after router integration**
- **Found during:** Task 1 verification
- **Issue:** `test_build_context_prompt_calls_generate_embedding` expected `generate_embedding("HbA1c results")` but the new code calls `route_query()` first which expands "HbA1c" → "hemoglobina glicada" via `expand_abbreviations()`, so embedding was called with the expanded query. Tests patched `generate_embedding` and `search` but not `route_query`.
- **Fix:** Updated all 3 active tests in `test_retriever.py` to mock `route_query` with a controlled `RoutingResult(intent="search_only", search_queries=[...])` for proper isolation.
- **Files modified:** `backend/tests/rag/test_retriever.py`
- **Commit:** `219e173` (same task commit)

## Known Stubs

- `test_context_includes_sql_section` — still `@pytest.mark.skip(reason="Wave 0 stub — implement after retriever.py refactored in Plan 05-04")`. This stub was originally written for post-05-04 implementation. The retriever is now refactored; however, per the plan structure the stub was left skipped as it was part of the Wave 0 test infrastructure and the acceptance criteria called for keeping it skipped.

## Self-Check: PASSED
