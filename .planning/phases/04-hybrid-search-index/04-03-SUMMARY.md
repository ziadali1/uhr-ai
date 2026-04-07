---
phase: 04-hybrid-search-index
plan: "03"
subsystem: rag
tags: [embeddings, context-block, azure-openai, tdd]
dependency_graph:
  requires: []
  provides: [assemble_context_block, generate_embedding]
  affects: [backend/services/rag/indexer.py, backend/services/rag/retriever.py]
tech_stack:
  added: [openai]
  patterns: [soft-fail, mock-guard, dispatch-on-family]
key_files:
  created:
    - backend/services/rag/context_block.py
    - backend/services/azure/embeddings.py
    - backend/tests/rag/test_context_block.py
    - backend/tests/rag/test_embeddings.py
    - backend/conftest.py
    - backend/tests/__init__.py
    - backend/tests/rag/__init__.py
  modified: []
decisions:
  - "conftest.py added at backend/ root to insert backend dir into sys.path for pytest imports"
  - "test files for context_block and embeddings created from scratch (no pre-existing stubs found)"
metrics:
  duration: "2min"
  completed_date: "2026-04-07"
  tasks_completed: 2
  files_changed: 7
---

# Phase 04 Plan 03: Context Block Assembly and Embedding Generation Summary

**One-liner:** context_block.py assembles structured plain-text embedding inputs from StructuredResult per document family; embeddings.py wraps Azure OpenAI text-embedding-3-small with mock-guard and soft-fail.

## What Was Built

Two new modules that form the core building blocks for the hybrid search index:

1. **`backend/services/rag/context_block.py`** — `assemble_context_block(sr, anonymized_text) -> str`
   - Dispatches on `sr.document_family` to reconstruct typed Pydantic models from `sr.structured_data`
   - Assembly order per D-02: entities_for_memory → summary → family-specific fields
   - Fallback to `anonymized_text[:1000]` when sr is None or block is empty (D-03)
   - Truncates output at 2000 chars (D-04)
   - try/except wraps dispatch so partial/malformed data never breaks assembly (Pitfall 3)

2. **`backend/services/azure/embeddings.py`** — `generate_embedding(text) -> list[float] | None`
   - Calls Azure OpenAI text-embedding-3-small deployment (D-06/D-07)
   - Deployment name from `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` env var (D-08)
   - Reuses `_use_mock()` pattern from `search.py`; mock mode returns None without calling Azure (D-24)
   - Soft-fail: any exception logs error and returns None (D-10)
   - `_get_embedding_client()` factory function enables patching in tests

3. **Test infrastructure**
   - `backend/conftest.py`: inserts backend directory into sys.path for clean module imports
   - `backend/tests/rag/test_context_block.py`: 7 tests covering all 4 families, fallback, truncation
   - `backend/tests/rag/test_embeddings.py`: 3 tests covering success path, failure path, mock mode

## Verification Results

```
cd backend && python -m pytest tests/rag/test_context_block.py tests/rag/test_embeddings.py -x -q
..........
10 passed in 1.46s
```

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| conftest.py at backend/ root adds backend to sys.path | No existing pytest config; needed for clean `from services.rag.context_block import` style imports |
| Test files created from scratch (no stubs) | No pre-existing test files with @pytest.mark.skip were found — Wave 0 test stubs did not exist yet |
| _get_embedding_client() as injectable factory | Allows patching in tests without environment variable setup |

## Deviations from Plan

### Auto-fixed Issues

None — plan executed exactly as written.

### Notes on Test Stubs

The plan referenced removing `@pytest.mark.skip` decorators from pre-existing test files. No such files existed; the test files were created from scratch per the `<behavior>` sections. All tests pass.

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| Task 1: context_block.py | 7d912da | feat(04-03): implement assemble_context_block() with structured context block assembly |
| Task 2: embeddings.py | 35d4e3d | feat(04-03): implement generate_embedding() with Azure OpenAI soft-fail pattern |

## Known Stubs

None — both modules are fully wired. context_block.py handles all 4 document families. generate_embedding() is complete with real Azure OpenAI calls (gated by mock mode).

## Self-Check: PASSED

- [x] backend/services/rag/context_block.py exists
- [x] backend/services/azure/embeddings.py exists
- [x] backend/tests/rag/test_context_block.py exists
- [x] backend/tests/rag/test_embeddings.py exists
- [x] Commits 7d912da and 35d4e3d exist
- [x] 10 tests pass
