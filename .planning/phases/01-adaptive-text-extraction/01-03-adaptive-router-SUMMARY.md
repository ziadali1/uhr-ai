---
phase: 01-adaptive-text-extraction
plan: 3
subsystem: extraction
tags: [router, adaptive-extraction, pymupdf, document-intelligence, tdd]
dependency_graph:
  requires:
    - 01-01-page-classifier (is_native_page)
    - 01-02-native-extraction-quality-score (extract_text_native, compute_quality_score)
  provides:
    - extract_text_adaptive (services.extraction.router)
    - extract_text_with_meta (services.azure.document_intelligence)
  affects:
    - backend/services/pipeline/orchestrator.py (zero changes needed)
    - 01-04-metadata-storage (consumes extract_text_with_meta)
tech_stack:
  added: []
  patterns:
    - Dependency injection: OCR callable passed to router to avoid circular import
    - Thin shim: document_intelligence delegates routing to services/extraction/router
    - TDD: tests written before implementation
key_files:
  created:
    - backend/services/extraction/router.py
    - backend/tests/extraction/test_router.py
  modified:
    - backend/services/azure/document_intelligence.py
decisions:
  - OCR callable injected into router as argument to prevent circular import between document_intelligence and router
  - Mock path in document_intelligence short-circuits before calling router to keep test environments fast
  - extract_text_with_meta() added as metadata-rich variant for Plan 4 to use when persisting extraction results
metrics:
  duration: "2min"
  completed: "2026-04-05T13:49:28Z"
  tasks_completed: 2
  files_created: 2
  files_modified: 1
  tests_added: 6
  tests_passing: 6
requirements:
  - INGEST-02
  - INGEST-03
---

# Phase 01 Plan 03: Adaptive Router Summary

**One-liner:** Adaptive extraction router wiring classifier + extractor into document_intelligence.py shim with quality-gated native/OCR routing.

## What Was Built

`services/extraction/router.py` — `extract_text_adaptive()` — the central routing function that decides between PyMuPDF native extraction and Azure OCR based on per-page classification and quality scoring.

`services/azure/document_intelligence.py` — updated to delegate to the adaptive router while keeping the `extract_text(file_bytes, filename) -> str` interface that `orchestrator.py` already uses. Added `extract_text_with_meta()` for Plan 4.

## Routing Logic Implemented

| Condition | Method | fallback_reason |
|-----------|--------|-----------------|
| Non-PDF filename | ocr | non_pdf |
| All pages native + score >= 0.65 | native | None |
| All pages native + score < 0.65 | ocr | low_quality |
| All pages scanned | ocr | None |
| Mixed pages (some native, some scanned) | ocr | mixed_pages |

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | Failing tests for router | f02d3cc | backend/tests/extraction/test_router.py |
| 1 (GREEN) | Implement extract_text_adaptive() | 5736bd7 | backend/services/extraction/router.py + test fix |
| 2 | Update document_intelligence.py | 07fea53 | backend/services/azure/document_intelligence.py |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed fitz.__version__ AttributeError in native-path test**
- **Found during:** Task 1, GREEN phase
- **Issue:** `test_all_native_high_score_uses_native` patched `fitz` as MagicMock; accessing `fitz.__version__` (used in the `library` return value) raised `AttributeError` because dunder attributes raise on MagicMock
- **Fix:** Added `mock_fitz.__version__ = "1.24.0"` inside the test context manager before calling `extract_text_adaptive`
- **Files modified:** backend/tests/extraction/test_router.py
- **Commit:** 5736bd7

## Known Stubs

None — all routing paths produce real output. Mock path in `document_intelligence.py` is intentional and explicitly gated by `USE_MOCK_AZURE` env var, not a stub.

## Self-Check: PASSED

See verification below.
