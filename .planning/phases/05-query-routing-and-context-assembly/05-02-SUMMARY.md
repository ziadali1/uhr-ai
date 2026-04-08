---
phase: 05-query-routing-and-context-assembly
plan: 02
subsystem: api
tags: [pydantic, supabase, llm, rag, query-routing, sql]

# Dependency graph
requires:
  - phase: 05-01
    provides: Wave 0 test stubs for router.py (test_router.py with skipped tests)
  - phase: 04-hybrid-search-index
    provides: services/azure/llm.py generate_json(), services/azure/search.py, services/supabase_store.py _get_client()
provides:
  - RoutingResult Pydantic model — structured query routing output
  - expand_abbreviations() — Portuguese medical abbreviation expansion before LLM call
  - route_query() — LLM-driven intent classification with mock guard and soft-fail
  - execute_sql_steps() — SQL template dispatcher scoped by user_id
  - _execute_single_step() — per-table Supabase SDK query templates
  - format_sql_block() — compact patient data context block for Claude's prompt
affects: [05-03, 05-04, 05-05]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Mock guard pattern (_use_mock_cache / _use_mock()) replicated from search.py
    - Soft-fail fallback: LLM failure returns search_only with original query (D-04)
    - SQL template pattern: LLM emits step keys, code dispatches to safe Supabase SDK chains
    - user_id always injected by code in SQL steps — LLM never touches it (D-07)
    - Token budget enforcement: format_sql_block caps at ~3200 chars (~800 tokens) (D-12)

key-files:
  created:
    - backend/services/rag/router.py
  modified: []

key-decisions:
  - "Mock guard in route_query() returns search_only immediately — avoids RoutingResult validation failure on '{}' from generate_json() in mock mode (Pitfall 2)"
  - "time_range typed as list[str] | None, NOT tuple[date, date] — Pydantic 2.x JSON serialization compatibility (Pitfall 5)"
  - "_ROUTER_SYSTEM_PROMPT uses f-string with date.today().isoformat() at module load time — acceptable for per-request service"
  - "format_sql_block() returns empty string for empty input, header+footer only omitted when no rows exist"

patterns-established:
  - "SQL step key format: '{table}:{qualifier}' or '{table}:{analyte}:range:{start}:{end}' — LLM emits keys, code dispatches to templates"
  - "Soft-fail pattern across all SQL steps: each step wrapped individually, failures logged and skipped"

requirements-completed: [RETRIEVE-04]

# Metrics
duration: 2min
completed: 2026-04-08
---

# Phase 05 Plan 02: Query Router Summary

**LLM-driven query router with abbreviation expansion, intent classification, Supabase SQL template executors, and structured context block formatter — all with mock guard and soft-fail.**

## Performance

- **Duration:** 2 min
- **Started:** 2026-04-08T10:38:37Z
- **Completed:** 2026-04-08T10:40:19Z
- **Tasks:** 2 completed
- **Files modified:** 1

## Accomplishments

- Created `backend/services/rag/router.py` implementing RETRIEVE-04: intent classification, entity extraction, temporal resolution, and safe structured data retrieval
- Implemented RoutingResult Pydantic model with correct list[str] types (avoids Pitfall 5 tuple serialization issue)
- Implemented 5 SQL template executors (observations, medications, conditions, allergies, imaging) all scoped by user_id injected by code
- format_sql_block() formats patient data within ~800 token budget per D-12

## Task Commits

Each task was committed atomically:

1. **Task 1: Create router.py — RoutingResult, expand_abbreviations, route_query** + **Task 2: Add SQL executor functions** - `5a458a1` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `backend/services/rag/router.py` — full router module: mock guard, abbreviation expansion, RoutingResult model, LLM interpreter, SQL dispatchers, context block formatter

## Verification Results

```
cd backend && python -c "
from services.rag.router import route_query, expand_abbreviations, RoutingResult, execute_sql_steps, format_sql_block
r = route_query('Qual meu HbA1c?', 'u1')
print('intent:', r.intent)                           # intent: search_only
print('expand:', expand_abbreviations('HbA1c e PA estão altos'))  # hemoglobina glicada e pressão arterial estão altos
print('sql block empty:', format_sql_block([]))      # (empty string)
"
```

Test suite: 16 passed, 17 skipped (all stubs), 0 failed.

## Deviations from Plan

None — plan executed exactly as written. Both tasks combined into one file creation commit since Task 2 appends to the same file created in Task 1.

## Known Stubs

None — router.py is fully functional. The `test_router.py` Wave 0 stubs remain skipped per plan design (they are scheduled for implementation in a later plan).

## Self-Check: PASSED

- `backend/services/rag/router.py` — FOUND
- Commit `5a458a1` — FOUND
