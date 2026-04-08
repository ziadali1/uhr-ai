---
phase: 05-query-routing-and-context-assembly
plan: 01
subsystem: testing
tags: [pytest, tdd, wave-0, stubs, rag, router]

# Dependency graph
requires:
  - phase: 04-hybrid-search-index
    provides: test infrastructure (conftest.py, test_retriever.py with 3 green tests)
provides:
  - Wave 0 test stubs for all RETRIEVE-04 and RETRIEVE-05 test cases (11 stubs in test_router.py)
  - New stub test_context_includes_sql_section in test_retriever.py
affects:
  - 05-02 (router intent classification — unskips test_route_* stubs)
  - 05-03 (SQL observations fetch — unskips test_sql_* stubs)
  - 05-04 (context assembly refactor — unskips test_chat_block_* stubs + test_context_includes_sql_section)
  - 05-05 (integration — all 12 stubs must be green)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Wave 0 deferred-import pattern: no module-level imports from non-existent modules; import placed inside test body as comment
    - @pytest.mark.skip for Wave 0 stubs (preferred over xfail when module does not exist yet)

key-files:
  created:
    - backend/tests/rag/test_router.py
  modified:
    - backend/tests/rag/test_retriever.py

key-decisions:
  - "import pytest added to test_retriever.py (was missing before adding skip decorator)"

patterns-established:
  - "Wave 0 pattern: all stubs use @pytest.mark.skip(reason='Wave 0 stub — implement after router.py created'); import inside test body as comment"

requirements-completed: [RETRIEVE-04, RETRIEVE-05]

# Metrics
duration: 5min
completed: 2026-04-08
---

# Phase 5 Plan 01: Wave 0 Test Stubs Summary

**11 Wave 0 skipped stubs in test_router.py + 1 new stub in test_retriever.py establishing the full test contract for RETRIEVE-04 and RETRIEVE-05 before any implementation**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-04-08T10:40:00Z
- **Completed:** 2026-04-08T10:45:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Created `backend/tests/rag/test_router.py` with 11 skipped stubs covering all router test cases (RETRIEVE-04: intent routing + RETRIEVE-05: context assembly)
- Appended `test_context_includes_sql_section` stub to `backend/tests/rag/test_retriever.py`; 3 existing tests remain green
- Full rag suite: 16 passed, 17 skipped, 0 failed, 0 errors

## Task Commits

Each task was committed atomically:

1. **Task 1: Create test_router.py with 11 Wave 0 stubs** - `d688cd8` (test)
2. **Task 2: Append test_context_includes_sql_section stub to test_retriever.py** - `84fb482` (test)

## Files Created/Modified
- `backend/tests/rag/test_router.py` - 11 Wave 0 skipped stubs for RETRIEVE-04 and RETRIEVE-05 test cases; deferred import pattern; no module-level import of services.rag.router
- `backend/tests/rag/test_retriever.py` - Added `import pytest` (previously missing) and appended `test_context_includes_sql_section` stub

## Decisions Made
- Added `import pytest` to test_retriever.py — it was missing but required for the new `@pytest.mark.skip` decorator on the appended stub. The existing 3 tests didn't use any pytest decorators so it wasn't needed before.

## Deviations from Plan

None - plan executed exactly as written.

(Minor addition: `import pytest` added to test_retriever.py as a necessary prerequisite for using `@pytest.mark.skip` — this was implied by the task but not explicitly called out as a deviation. It's part of the plan action description: "Also add `import pytest` at the top of the file if not already present.")

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Wave 0 complete: all 12 stubs in place (11 in test_router.py + 1 in test_retriever.py)
- Plan 05-02 can unskip and implement test_route_* stubs (router intent classification)
- Plan 05-03 can unskip and implement test_sql_* stubs (SQL observations fetch)
- Plan 05-04 can unskip and implement test_chat_block_* stubs + test_context_includes_sql_section
- Plan 05-05 validates full integration path

---
*Phase: 05-query-routing-and-context-assembly*
*Completed: 2026-04-08*
