---
phase: 05-query-routing-and-context-assembly
plan: 03
subsystem: backend/services/rag
tags: [rag, context-assembly, structured-result, clinical-blocks, supabase, soft-fail]
dependency_graph:
  requires:
    - "05-01: Wave 0 test stubs (test_router.py)"
    - "05-02: router.py core (route_query, execute_sql_steps, format_sql_block)"
    - "04-03: context_block.py (family dispatch reference — read-only)"
  provides:
    - "backend/services/rag/router.py: assemble_chat_block() and _fetch_structured_result()"
  affects:
    - "05-04: retriever.py refactor will call assemble_chat_block() instead of raw excerpt"
tech_stack:
  added: []
  patterns:
    - "Soft-fail pattern: try/except wrapping Supabase fetch, returns None on any error"
    - "Family dispatch: if/elif per document_family, with fallback to excerpt for unknown"
    - "1200-char cap applied at block return boundary"
key_files:
  created: []
  modified:
    - backend/services/rag/router.py
decisions:
  - "models.document imported in router.py (not re-exported from context_block.py) — D-10: context_block.py is read-only"
  - "assemble_chat_block uses excerpt[:400] fallback for unknown family and exception in dispatch — same soft-fail principle as D-04"
  - "entities resolved as lab.entities_for_memory OR sr.entities_for_memory (family-specific first, top-level as fallback)"
metrics:
  duration: "4min"
  completed: "2026-04-08"
  tasks_completed: 1
  files_modified: 1
---

# Phase 05 Plan 03: Chat Context Assembler Summary

**One-liner:** Supabase-backed chat context assembler that produces D-11 `[Fonte: source | family | date]` clinical blocks from structured_result with soft-fail fallback to raw excerpt.

## What Was Built

Two functions appended to `backend/services/rag/router.py`:

**`_fetch_structured_result(doc_id: str) -> StructuredResult | None`**
- Queries `documents` table via Supabase SDK: `.table("documents").select("structured_result").eq("id", doc_id).single()`
- Returns `StructuredResult` Pydantic model parsed from JSONB column
- Soft-fail: logs warning and returns `None` on any exception (missing env vars, doc not found, schema error)

**`assemble_chat_block(doc_id, source_name, excerpt, collection_date) -> str`**
- Produces compact clinical block per D-11: `[Fonte: {source_name} | {family} | {date}]`
- Family dispatch: `structured_lab`, `imaging_narrative`, `clinical_narrative`, `medication_document`, unknown fallback
- Each family renders: Summary + Findings (formatted per family type) + Entities
- Block capped at 1200 chars (~300 tokens)
- Soft-fail: returns `{header}\n{excerpt[:400]}` when structured_result unavailable

## Acceptance Criteria Verified

| Criterion | Result |
|-----------|--------|
| `def assemble_chat_block(` in router.py | PASS |
| `def _fetch_structured_result(` in router.py | PASS |
| `table("documents")` in router.py | PASS |
| soft-fail path returns `[Fonte: Lab Test` | PASS |
| output capped at 1200 chars | PASS |
| no import from services.rag.context_block | PASS |
| pytest tests/rag/ exits 0 | PASS (16 passed, 17 skipped) |

## Deviations from Plan

**Deviation: Rebased worktree onto main before implementation**

- **Found during:** Pre-task setup
- **Issue:** Worktree was at commit 8a14a87 (before 05-02 and 04-03 commits). `backend/services/rag/router.py` and `backend/services/azure/embeddings.py` did not exist.
- **Fix:** Ran `git rebase main` to incorporate 05-02's router.py and all Phase 4 artifacts. Then appended 05-03 functions on top of the existing router.py.
- **Impact:** None — rebase was clean with no conflicts.

## Known Stubs

None — `assemble_chat_block()` is fully functional. The soft-fail path handles missing structured_result, but the function itself is complete and wired correctly to Supabase.

## Self-Check

Verified:
- `backend/services/rag/router.py` contains `def assemble_chat_block` and `def _fetch_structured_result`
- Commit 52e9da8 exists in git log
- pytest tests/rag/ — 16 passed, 17 skipped, 0 failed
