---
phase: 01-adaptive-text-extraction
plan: 01
subsystem: api
tags: [pymupdf, fitz, pdf, text-extraction, classification, pytest]

# Dependency graph
requires: []
provides:
  - "is_native_page() function in backend/services/extraction/classifier.py"
  - "pymupdf==1.24.5 dependency in requirements.txt"
  - "backend/services/extraction/ Python package"
  - "7 passing unit tests for page classifier"
affects: [01-02, 01-03, 01-04, 01-05]

# Tech tracking
tech-stack:
  added: [pymupdf==1.24.5]
  patterns:
    - "Return plain dict (not dataclass) from classifier to avoid circular imports with orchestrator"
    - "Mock fitz.Page with MagicMock in unit tests — no real PDF file required"
    - "Three-signal classification: char_count >= 50, image_coverage < 0.60, has_real_fonts"

key-files:
  created:
    - backend/services/extraction/__init__.py
    - backend/services/extraction/classifier.py
    - backend/tests/__init__.py
    - backend/tests/extraction/__init__.py
    - backend/tests/extraction/test_classifier.py
  modified:
    - backend/requirements.txt

key-decisions:
  - "Use plain dict return from is_native_page() to avoid circular imports with orchestrator layer"
  - "Detect fake fonts via GlyphLessFont name AND size-0 spans — both indicate OCR artifact pages"
  - "Image coverage threshold set at 0.60 (60%) matching research spec"
  - "Character threshold set at 50 printable chars per research spec"

patterns-established:
  - "TDD: write failing tests first, then implement until all pass"
  - "Unit tests mock fitz.Page entirely — no dependency on real PDF files"
  - "services/extraction/ package holds all PDF extraction logic"

requirements-completed: [INGEST-01]

# Metrics
duration: 2min
completed: 2026-04-05
---

# Phase 01 Plan 01: Page Classifier Summary

**pymupdf-based per-page native text classifier using three deterministic signals: char count, image coverage ratio, and real-font detection via span analysis**

## Performance

- **Duration:** 2 min
- **Started:** 2026-04-05T13:35:56Z
- **Completed:** 2026-04-05T13:38:00Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- pymupdf==1.24.5 added to requirements.txt and installed; fitz importable from Python
- `services/extraction/` package created with `is_native_page()` classifier
- Classifier correctly handles all edge cases: GlyphLessFont, size-0 fonts, image-dominant pages, mixed real/fake fonts
- 7 unit tests pass using MagicMock — no real PDF file dependency

## Task Commits

Each task was committed atomically:

1. **Task 1: Add pymupdf and create services/extraction package** - `f12ee3b` (feat)
2. **Task 2: Implement is_native_page() classifier with tests** - `0218ff2` (feat)

**Plan metadata:** (docs commit pending)

_Note: TDD tasks — tests written and confirmed failing before implementation_

## Files Created/Modified
- `backend/requirements.txt` - Added pymupdf==1.24.5 under PDF native extraction section
- `backend/services/extraction/__init__.py` - Package marker (empty)
- `backend/services/extraction/classifier.py` - is_native_page() and _has_real_fonts() implementation
- `backend/tests/__init__.py` - Test package marker (empty)
- `backend/tests/extraction/__init__.py` - Test sub-package marker (empty)
- `backend/tests/extraction/test_classifier.py` - 7 unit tests covering all classification scenarios

## Decisions Made
- Returned plain dict from `is_native_page()` instead of dataclass to prevent circular imports when the orchestrator (Plan 03) imports this module
- Font reality checked via both basefont name (GlyphLessFont blocklist) AND span size (> 0 required) — either condition alone insufficient
- `_has_real_fonts()` iterates all page spans, so mixed-font pages (some real, some fake) correctly resolve to True

## Deviations from Plan

None — plan executed exactly as written.

Minor note: the plan's verify command `python -c "import fitz; print(fitz.__version__)"` would fail because pymupdf exposes version as `fitz.version` (tuple), not `fitz.__version__`. The installation succeeded and `fitz.version` prints `('1.24.5', '1.24.2', '20240530000001')`. Functionality unaffected.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required. pymupdf installed locally via pip.

## Next Phase Readiness
- `is_native_page(page)` ready for Plan 02 (quality scorer) and Plan 03 (adaptive router)
- All downstream plans can import via: `from services.extraction.classifier import is_native_page`
- Test infrastructure (`backend/tests/`) established for all subsequent plans

---
*Phase: 01-adaptive-text-extraction*
*Completed: 2026-04-05*
