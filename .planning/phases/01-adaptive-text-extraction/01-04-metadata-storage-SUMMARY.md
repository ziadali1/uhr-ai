---
phase: 01-adaptive-text-extraction
plan: 4
subsystem: extraction-metadata
tags: [pydantic, supabase, upload-pipeline, extraction-metadata, tdd]
dependency_graph:
  requires:
    - 01-03-adaptive-router (extract_text_with_meta() function)
    - backend/services/extraction/router.py (extract_text_adaptive)
    - backend/services/azure/document_intelligence.py (extract_text_with_meta)
  provides:
    - ExtractionMeta Pydantic model
    - DocumentDetail.text_extraction_meta field
    - supabase_store JSONB persistence for text_extraction_meta
    - upload.py extraction metadata wiring
  affects:
    - 01-05-edge-cases (can now read extraction_meta for fallback logic)
    - supabase documents table (migration required for text_extraction_meta column)
tech_stack:
  added: []
  patterns:
    - TDD (red-green cycle for Pydantic model and DocumentDetail integration)
    - Optional JSONB field with graceful try/except pending column migration
key_files:
  created:
    - backend/tests/extraction/test_metadata_storage.py
  modified:
    - backend/models/document.py
    - backend/services/supabase_store.py
    - backend/api/upload.py
    - backend/services/pipeline/orchestrator.py
decisions:
  - "Pipeline orchestrator updated to use extract_text_with_meta() to avoid double extraction; exposes extraction_result dict in PipelineResult"
  - "supabase_store.save() text_extraction_meta INSERT wrapped in try/except pending Supabase migration"
  - "upload.py constructs ExtractionMeta from pipeline result (not a second extraction call) for efficiency"
metrics:
  duration: "3min"
  completed_date: "2026-04-05"
  tasks_completed: 2
  files_changed: 5
---

# Phase 1 Plan 4: Metadata Storage Summary

ExtractionMeta Pydantic model + DocumentDetail field + Supabase JSONB persistence + upload wiring for text extraction metadata.

## What Was Built

Every document upload now captures and persists structured extraction metadata:
- `ExtractionMeta` Pydantic model with method, quality_score, page_strategies, library, fallback_reason, extracted_at
- `DocumentDetail.text_extraction_meta` optional field (backward compatible with all existing documents)
- `supabase_store.save()` writes `text_extraction_meta` as JSONB, `_row_to_detail()` hydrates it on read
- `upload.py` constructs `ExtractionMeta` from the pipeline's extraction result and passes it to `DocumentDetail`
- Pipeline orchestrator updated to use `extract_text_with_meta()` and expose `extraction_result` in `PipelineResult`

## Supabase Migration Required

The `documents` table does not yet have the `text_extraction_meta` column. Run the following migration:

```sql
ALTER TABLE documents ADD COLUMN IF NOT EXISTS text_extraction_meta JSONB;
```

Until this migration runs, the INSERT will silently skip the column (wrapped in try/except). Existing uploads are unaffected.

## Task Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 (RED) | 68eb22a | test(01-04): failing tests for ExtractionMeta model |
| 1 (GREEN) | 95eb1d8 | feat(01-04): ExtractionMeta model + DocumentDetail field |
| 2 | fbf2732 | feat(01-04): persist text_extraction_meta, wire upload.py |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Avoided double extraction by updating orchestrator**
- **Found during:** Task 2
- **Issue:** The plan suggested calling `extract_text_with_meta()` directly in upload.py, but the orchestrator also calls `extract_text()` internally, which would result in double extraction (2x cost and latency in production)
- **Fix:** Updated `orchestrator.run()` to call `extract_text_with_meta()` instead of `extract_text()` and expose the result in `PipelineResult.extraction_result`. Upload.py constructs `ExtractionMeta` from this field.
- **Files modified:** `backend/services/pipeline/orchestrator.py`, `backend/api/upload.py`
- **Commit:** fbf2732

## Known Stubs

None - all data is wired end-to-end. The `text_extraction_meta` column write will be silently skipped until the Supabase migration is applied.

## Self-Check: PASSED

All files exist. All commits verified (68eb22a, 95eb1d8, fbf2732). All 6 tests pass.
