---
phase: 04-hybrid-search-index
plan: 01
subsystem: testing
tags: [pytest, rag, azure-ai-search, embeddings, hybrid-search, wave-0-stubs]

requires:
  - phase: 03-migration-and-backfill
    provides: patient tables and structured data available for context retrieval

provides:
  - Wave 0 test stubs for all Phase 4 RAG modules (21 tests, all skipped)
  - backend/tests/rag/ package with 6 test files covering schema, context, embeddings, indexer, retriever
  - pytest-discoverable test targets for Plans 04-02 through 04-05 to turn green

affects:
  - 04-02 (search schema builder — 5 stubs to turn green)
  - 04-03 (context block + embeddings — 10 stubs to turn green)
  - 04-04 (indexer update — 3 stubs to turn green)
  - 04-05 (hybrid retriever — 3 stubs to turn green)

tech-stack:
  added: []
  patterns:
    - "Wave 0 stubs: all test functions use @pytest.mark.skip(reason='Wave 0 stub — implementation in Plan XX')"
    - "sys.path.insert(0, ...) pattern for test imports (consistent with test_classifier.py)"

key-files:
  created:
    - backend/tests/__init__.py
    - backend/tests/rag/__init__.py
    - backend/tests/rag/test_search_schema.py
    - backend/tests/rag/test_context_block.py
    - backend/tests/rag/test_embeddings.py
    - backend/tests/rag/test_indexer.py
    - backend/tests/rag/test_retriever.py
  modified: []

key-decisions:
  - "All Wave 0 stubs use @pytest.mark.skip (not xfail) — clearer intent that code under test does not yet exist"
  - "tests/__init__.py added at backend/tests/ level to match main repo structure for discovery"

patterns-established:
  - "Wave 0 stub pattern: import inside test function body so import error does not prevent collection"

requirements-completed:
  - RETRIEVE-01
  - RETRIEVE-02
  - RETRIEVE-03

duration: 2min
completed: 2026-04-07
---

# Phase 4 Plan 01: Wave 0 Test Stubs Summary

**21 pytest-discoverable Wave 0 stubs created across 5 test files for all Phase 4 hybrid search modules — schema, context, embeddings, indexer, retriever**

## Performance

- **Duration:** 2 min
- **Started:** 2026-04-07T10:05:22Z
- **Completed:** 2026-04-07T10:07:22Z
- **Tasks:** 1 of 2 automated (Task 2 is a checkpoint:human-action requiring Azure portal verification)
- **Files modified:** 7

## Accomplishments

- Created `backend/tests/rag/` package with 6 test files covering all Phase 4 modules
- 21 Wave 0 stubs discoverable by pytest — all marked `@pytest.mark.skip`
- Test targets established for Plans 04-02 (5 stubs), 04-03 (10 stubs), 04-04 (3 stubs), 04-05 (3 stubs)
- Import pattern (imports inside test body) ensures collection never fails even before modules exist

## Task Commits

1. **Task 1: Create Wave 0 test stubs for all Phase 4 modules** - `8b7e3c7` (test)
2. **Task 2: Verify Azure AI Search tier** — CHECKPOINT (human-action required)

## Files Created/Modified

- `backend/tests/__init__.py` — package init for test discovery
- `backend/tests/rag/__init__.py` — RAG test package init
- `backend/tests/rag/test_search_schema.py` — 5 stubs for RETRIEVE-01 (index schema with vector field)
- `backend/tests/rag/test_context_block.py` — 7 stubs for RETRIEVE-02 (context block assembly per document family)
- `backend/tests/rag/test_embeddings.py` — 3 stubs for RETRIEVE-02 (generate_embedding function)
- `backend/tests/rag/test_indexer.py` — 3 stubs for RETRIEVE-02 (indexer with vector support)
- `backend/tests/rag/test_retriever.py` — 3 stubs for RETRIEVE-03 (hybrid search retriever)

## Decisions Made

- All stubs use `@pytest.mark.skip` (not `@pytest.mark.xfail`) — skip is cleaner for Wave 0 where the module under test does not exist at all
- Imports placed inside test function bodies — prevents ImportError from blocking collection when modules don't yet exist
- `tests/__init__.py` added to match main-repo structure (main repo already has this file)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added backend/tests/__init__.py**
- **Found during:** Task 1 (test collection verification)
- **Issue:** Worktree had `backend/tests/rag/` but no `backend/tests/__init__.py` — main repo has this file and pytest discovery depends on it
- **Fix:** Created empty `backend/tests/__init__.py` matching the main repo pattern
- **Files modified:** `backend/tests/__init__.py`
- **Verification:** `pytest --collect-only` discovered all 21 tests
- **Committed in:** `8b7e3c7` (part of Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 missing critical)
**Impact on plan:** Essential for correct pytest discovery. No scope creep.

## Issues Encountered

None.

## User Setup Required

**Task 2 requires manual Azure portal verification:**
1. Go to Azure Portal -> Azure AI Search service -> Overview -> check Pricing tier (must be Basic or higher)
2. Go to Azure Portal -> Azure OpenAI -> Deployments -> confirm `text-embedding-3-small` deployment exists
3. Set `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` env var in `backend/.env`

Verification command after setup:
```bash
cd backend && python -c "import os; from dotenv import load_dotenv; load_dotenv(); assert os.environ.get('AZURE_OPENAI_EMBEDDING_DEPLOYMENT'), 'AZURE_OPENAI_EMBEDDING_DEPLOYMENT not set'; print('env var ok')"
```

## Next Phase Readiness

- Wave 0 stubs complete — Plan 04-02 (search schema builder) has 5 test targets to turn green
- Azure tier verification (Task 2) must be completed before Plan 04-02 starts index creation
- All test files import inside test function bodies — safe to run with or without implementations

## Known Stubs

All stubs are intentional Wave 0 placeholders. The stub design is the plan's deliverable — there are no unintentional stubs.

---
*Phase: 04-hybrid-search-index*
*Completed: 2026-04-07*
