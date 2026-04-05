---
phase: 01-adaptive-text-extraction
plan: 2
subsystem: backend/extraction
tags: [extraction, quality-scoring, pymupdf, tdd]
dependency_graph:
  requires: [01-01-page-classifier]
  provides: [extract_text_native, compute_quality_score]
  affects: [01-03-extraction-router]
tech_stack:
  added: []
  patterns: [4-signal-weighted-scoring, per-page-extraction, acroform-widget-collection]
key_files:
  created:
    - backend/services/extraction/extractor.py
    - backend/tests/extraction/test_extractor.py
  modified: []
key_decisions:
  - "Line length signal gates on printable-char presence to avoid false positives on pure garbage blobs"
  - "Imports fitz at module level (not deferred) since module is only loaded when extraction is needed"
metrics:
  duration: 2min
  completed: "2026-04-05"
  tasks_completed: 2
  files_created: 2
  files_modified: 0
requirements: [INGEST-02, INGEST-04]
---

# Phase 1 Plan 2: Native Extraction and Quality Score Summary

**One-liner:** PyMuPDF per-page text extraction with AcroForm widget support, and a 4-signal weighted quality scorer (printable ratio 0.40, word density 0.35, line length 0.15, numeric density 0.10).

## What Was Built

Two functions in `backend/services/extraction/extractor.py`:

**`extract_text_native(file_bytes: bytes) -> str`**
- Opens PDF via `fitz.open(stream=..., filetype="pdf")`
- Iterates pages in order, calls `is_native_page()` from Plan 1's classifier
- Native pages: calls `page.get_text("text")`, then iterates `page.widgets()` for AcroForm field values (MEMED prescriptions, iClinic forms)
- Non-native pages contribute empty string
- Returns all page texts joined by newline

**`compute_quality_score(text: str) -> float`**
- Signal 1 (0.40): printable char ratio — chars in `string.printable` or not in unicode category Cc/Cs
- Signal 2 (0.35): word-like token density — `\b[a-zA-ZÀ-ÿ]{2,}\b` matches / total tokens, capped at 1.0
- Signal 3 (0.15): avg line length / 60.0, capped at 1.0 — lines must contain printable chars
- Signal 4 (0.10): numeric token count / word count / 0.15, capped at 1.0
- Returns `round(clamp(sum, 0.0, 1.0), 4)`

## Tests (9 total, all passing)

**compute_quality_score (6 tests):**
- Empty string → 0.0
- Whitespace-only → 0.0
- Good medical text (GOOD_MEDICAL_TEXT fixture) → >= 0.65
- Pure non-printable garbage → < 0.10
- All inputs stay in [0.0, 1.0]
- Near-perfect text → >= 0.85

**extract_text_native (3 tests using mocks):**
- Single native page: text is returned
- Mixed pages: non-native page content excluded
- Widget values appended to page text

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed line_length_score false positive on pure garbage**
- **Found during:** Task 2 TDD GREEN — `test_score_non_printable_chars` was failing (score was 0.15 instead of < 0.10)
- **Issue:** Garbage blob `"\x00\x01\x02\x03\x04\x05" * 50` has no newlines, so `.splitlines()` returned one "line" of 300 chars. `avg_line_length = 300`, `line_length_score = 1.0`, contributing 0.15 to score despite zero printable content.
- **Fix:** Line filter now requires at least one printable character per line: `any(c in string.printable or unicodedata.category(c) not in ("Cc", "Cs") for c in line)`. When no printable lines exist, `avg_line_length = 0.0` and `line_length_score = 0.0`.
- **Files modified:** `backend/services/extraction/extractor.py`
- **Commit:** a120273

## Known Stubs

None — both functions are fully implemented with real logic wired to their data sources.

## Self-Check: PASSED

- [x] `backend/services/extraction/extractor.py` exists
- [x] `backend/tests/extraction/test_extractor.py` exists
- [x] commit f2e2abd (test RED: extract_text_native) exists
- [x] commit 0d857cd (feat GREEN: extract_text_native) exists
- [x] commit c8815fa (test RED: compute_quality_score) exists
- [x] commit a120273 (feat GREEN: compute_quality_score + bug fix) exists
- [x] All 9 tests pass
- [x] Weights 0.40, 0.35, 0.15, 0.10 present in source
- [x] `page.widgets()` called in extract_text_native
