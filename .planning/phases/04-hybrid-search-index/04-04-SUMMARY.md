---
phase: 04-hybrid-search-index
plan: "04"
subsystem: rag-indexer
tags: [rag, embeddings, context-block, indexer, upload-pipeline]
dependency_graph:
  requires: ["04-02", "04-03"]
  provides: ["RETRIEVE-02"]
  affects: ["backend/services/rag/indexer.py", "backend/api/upload.py"]
tech_stack:
  added: []
  patterns: ["context-block-assembly", "soft-fail-embedding", "backward-compatible-signature"]
key_files:
  created: []
  modified:
    - backend/services/rag/indexer.py
    - backend/api/upload.py
    - backend/tests/rag/test_indexer.py
decisions:
  - "structured_result defaults to None in index_after_upload — backward-compatible with all existing callers"
  - "collection_date extracted from structured_data dict, not top-level StructuredResult field — matches existing data shape"
metrics:
  duration: "2min"
  completed_date: "2026-04-07"
  tasks_completed: 2
  files_modified: 3
---

# Phase 04 Plan 04: Indexer Context Block + Embedding Wiring Summary

**One-liner:** Indexer now assembles a structured context block and generates an embedding before calling index_document, with soft-fail on embedding failure; upload.py passes structured_result to close the pipeline loop.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (TDD) | Update indexer.py — context block + embedding | eb14013, 055d05d | indexer.py, test_indexer.py |
| 2 | Wire structured_result into upload.py | b6d4b43 | upload.py |

## What Was Built

### Task 1: indexer.py rewrite (TDD)

`index_after_upload()` now:
1. Calls `assemble_context_block(structured_result, anonymized_text)` to build embedding input
2. Calls `generate_embedding(context_block)` — soft-fail returns None without blocking indexing
3. Extracts `document_family`, `document_subtype`, `collection_date` from `structured_result`
4. Passes `content_vector`, `document_family`, `collection_date`, `document_subtype` to `index_document()`

New signature: `structured_result: StructuredResult | None = None` — backward-compatible.

### Task 2: upload.py wiring

Added `structured_result=result.structured_result` to the `index_after_upload()` call. One-line change — closes the data flow from pipeline output to search index.

## Verification

- `cd backend && python -m pytest tests/rag/test_indexer.py -x -q` — 3 passed
- `cd backend && python -c "from api.upload import router"` — import ok
- All acceptance criteria met (imports, signature, logic, no skip decorators)

## Deviations from Plan

### Auto-actions

**Merge main before execution** — worktree branch was missing context_block.py and embeddings.py from Plans 04-02/04-03. Merged main (fast-forward) to bring in dependencies. Not a deviation — precondition for the plan to run.

None beyond the merge — plan executed as written.

## Known Stubs

None — all data flows are wired. content_vector will be None in mock mode (USE_MOCK_AZURE=true) by design (D-24), not a stub.

## Self-Check: PASSED

- indexer.py: FOUND
- upload.py: FOUND
- SUMMARY.md: FOUND
- Commits b6d4b43, 055d05d, eb14013: FOUND
