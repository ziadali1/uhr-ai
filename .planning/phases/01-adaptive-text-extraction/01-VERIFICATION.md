---
phase: 01-adaptive-text-extraction
verified: 2026-04-05T15:00:00Z
status: passed
score: 6/6 must-haves verified
re_verification:
  previous_status: gaps_found
  previous_score: 5/6
  gaps_closed:
    - "Password-protected PDFs return HTTP 422 with Portuguese error message"
    - "Corrupt/truncated PDF attempts OCR fallback with fallback_reason='corrupt_pdf'"
    - "QR code pages are reclassified as non-native via _apply_qr_code_guard()"
    - "backend/tests/extraction/test_edge_cases.py exists with 8 passing tests"
  gaps_remaining: []
  regressions: []
---

# Phase 1: Adaptive Text Extraction Verification Report

**Phase Goal:** Stop sending native-text PDFs through OCR. Detect, extract natively, score quality, and fall back to OCR only when necessary.
**Verified:** 2026-04-05T15:00:00Z
**Status:** PASSED
**Re-verification:** Yes — after edge-case code merged into main (commit af9f959)

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | A per-page classifier detects native vs. image/scanned pages using char count, image coverage, and font analysis | VERIFIED | `backend/services/extraction/classifier.py` — `is_native_page()` fully implemented; 7 passing tests |
| 2 | extract_text_native() extracts text from all native pages with AcroForm widget support | VERIFIED | `backend/services/extraction/extractor.py` — full implementation; 3 passing tests |
| 3 | compute_quality_score() returns float in [0,1] using 4-signal weighted formula | VERIFIED | `backend/services/extraction/extractor.py` — 4 signals at weights 0.40/0.35/0.15/0.10; 6 passing tests |
| 4 | extract_text() routes native-text PDFs to PyMuPDF (score >= 0.65) and falls back to OCR otherwise, without changing the caller interface | VERIFIED | `backend/services/extraction/router.py` + `backend/services/azure/document_intelligence.py` — routing wired; orchestrator unchanged; 6 passing tests |
| 5 | Extraction metadata (method, quality_score, library, fallback_reason, page_strategies) is stored with every document | VERIFIED | `ExtractionMeta` in `models/document.py`, `text_extraction_meta` field on `DocumentDetail`, supabase_store saves it, upload.py threads it through orchestrator result; 6 passing tests |
| 6 | Password-protected PDFs return HTTP 422; corrupt PDFs fall back to OCR; QR code pages are reclassified as non-native | VERIFIED | `PasswordProtectedError` class at router.py:34; `doc.authenticate("")` guard at router.py:117-122; `except Exception` around `fitz.open()` at router.py:100-113 with `fallback_reason="corrupt_pdf"`; `_apply_qr_code_guard()` at router.py:46-58; `except PasswordProtectedError` → HTTP 422 at upload.py:118-122; 8 tests in test_edge_cases.py all pass |

**Score:** 6/6 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/requirements.txt` | pymupdf dependency declared | VERIFIED | `pymupdf==1.24.5` |
| `backend/services/extraction/__init__.py` | Package marker | VERIFIED | File exists |
| `backend/services/extraction/classifier.py` | `is_native_page()` function | VERIFIED | Exports `is_native_page`, all signals implemented |
| `backend/tests/extraction/test_classifier.py` | 7 pytest tests | VERIFIED | 7 tests, all pass |
| `backend/services/extraction/extractor.py` | `extract_text_native()` and `compute_quality_score()` | VERIFIED | Both exported, all signals at spec weights |
| `backend/tests/extraction/test_extractor.py` | 9 pytest tests | VERIFIED | 9 tests, all pass |
| `backend/services/extraction/router.py` | `extract_text_adaptive()` with edge-case guards | VERIFIED | `PasswordProtectedError` at line 34; corrupt guard at lines 100-113; QR guard at lines 46-58 and called at line 135; all routing paths present |
| `backend/services/azure/document_intelligence.py` | Delegates to adaptive router | VERIFIED | Contains `extract_text_adaptive` delegation, mock bypass path, `extract_text_with_meta()` |
| `backend/tests/extraction/test_router.py` | 6 pytest tests for routing | VERIFIED | 6 tests, all pass |
| `backend/models/document.py` | `ExtractionMeta` model and `text_extraction_meta` on `DocumentDetail` | VERIFIED | `ExtractionMeta` at line 6, `DocumentDetail.text_extraction_meta` at line 152 |
| `backend/services/supabase_store.py` | Writes `text_extraction_meta` in INSERT | VERIFIED | Lines 43-47 write to row, lines 86-90 hydrate on read |
| `backend/api/upload.py` | Calls `extract_text_with_meta`, builds `ExtractionMeta`, handles PasswordProtectedError → 422 | VERIFIED | `PasswordProtectedError` imported at line 17; `except PasswordProtectedError` → HTTP 422 at lines 118-122; ExtractionMeta built from `result.extraction_result` at lines 93-102 |
| `backend/tests/extraction/test_metadata_storage.py` | 6 tests for meta model | VERIFIED | 6 tests, all pass |
| `backend/tests/extraction/test_edge_cases.py` | 8 tests for edge cases | VERIFIED | File exists; 8 tests — password protection (2), corrupt PDF (1), avg_line_length helpers (2), QR guard (2), AcroForm (1) — all 8 pass |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `classifier.py` | fitz (pymupdf) | `import fitz` | VERIFIED | Used via page argument passed from extractor |
| `test_classifier.py` | `classifier.py` | `from services.extraction.classifier import is_native_page` | VERIFIED | Import present and used |
| `extractor.py` | fitz | `import fitz` | VERIFIED | Module-level import |
| `extractor.py` | `classifier.py` | `from services.extraction.classifier import is_native_page` | VERIFIED | Module-level import |
| `router.py` | `extractor.py` | `from services.extraction.extractor import ...` | VERIFIED | Module-level import |
| `document_intelligence.py` | `router.py` | `from services.extraction.router import extract_text_adaptive` | VERIFIED | Lazy import guarded by mock check |
| `orchestrator.py` | `document_intelligence.py` | `from services.azure.document_intelligence import extract_text_with_meta` | VERIFIED | Line 18; `run()` calls it |
| `upload.py` | `document_intelligence.py` | `from services.azure.document_intelligence import extract_text_with_meta` | VERIFIED | Imported; usage routed through orchestrator |
| `supabase_store.py` | `models/document.py` | `detail.text_extraction_meta.model_dump()` | VERIFIED | Lines 43-47 |
| `upload.py` | `router.py` | `PasswordProtectedError` caught → HTTPException 422 | VERIFIED | `from services.extraction.router import PasswordProtectedError` at line 17; `except PasswordProtectedError as e: raise HTTPException(status_code=422, ...)` at lines 118-122 |
| `test_edge_cases.py` | `router.py` | imports `PasswordProtectedError`, `_avg_line_length`, `_apply_qr_code_guard` | VERIFIED | All three symbols imported at lines 9-13; used in 8 tests |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `upload.py` | `extraction_meta` | `result.extraction_result` from `orchestrator.run()` → `extract_text_with_meta()` | Yes — real dict from adaptive router | FLOWING |
| `supabase_store.py` | `row["text_extraction_meta"]` | `detail.text_extraction_meta.model_dump()` | Yes — populated by upload pipeline | FLOWING |
| `document_intelligence.py` mock path | Returns static mock dict | Hardcoded `_MOCK_TEXT` with `method="ocr"` | Static (intentional mock for dev) | STATIC (expected) |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All 5 test suites pass (36 tests total) | `cd backend && python -m pytest tests/extraction/ -v` | 36 passed in 0.25s | PASS |
| `PasswordProtectedError` importable from router | Verified by test_edge_cases.py import at line 10 | import succeeds; used in test at line 31 | PASS |
| Password-protected PDF raises PasswordProtectedError | `test_password_protected_raises_error` | PASSED | PASS |
| Print-only protection proceeds normally | `test_print_only_protection_proceeds_normally` | PASSED | PASS |
| Corrupt PDF returns fallback_reason="corrupt_pdf" | `test_corrupt_pdf_falls_back_to_ocr` | PASSED | PASS |
| QR long-line pages reclassified as non-native | `test_qr_code_guard_reclassifies_long_line_pages` | PASSED | PASS |
| Normal pages pass QR guard unchanged | `test_qr_code_guard_preserves_normal_pages` | PASSED | PASS |
| AcroForm widget values included in native text | `test_acroform_widget_values_included_in_native_text` | PASSED | PASS |
| upload.py catches PasswordProtectedError → 422 | grep: `except PasswordProtectedError` at upload.py:118 | `status_code=422` confirmed | PASS |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| INGEST-01 | 01-01 | Detect whether a PDF has native text (char density, image coverage, font analysis) | SATISFIED | `is_native_page()` in classifier.py; 7 tests pass |
| INGEST-02 | 01-02, 01-03 | Extract text natively when quality score >= 0.65 | SATISFIED | `extract_text_native()` + router quality threshold logic |
| INGEST-03 | 01-03 | Fall back to Azure Document Intelligence OCR when native extraction absent or low quality | SATISFIED | Router fallback paths in `extract_text_adaptive()` |
| INGEST-04 | 01-02 | Compute deterministic quality score [0,1] for each extracted text version | SATISFIED | `compute_quality_score()` with 4-signal weighted formula |
| INGEST-05 | 01-04 | Store extraction metadata with each document in `text_extraction_meta` JSONB column | SATISFIED | `ExtractionMeta` model, supabase_store writes it, upload.py builds it |
| INGEST-06 | 01-05 | Handle medical PDF edge cases: password-protected, corrupt, AcroForm, ICP-Brasil | SATISFIED | `PasswordProtectedError` + HTTP 422 handler; corrupt fitz.open() fallback; QR guard; AcroForm via page.widgets(); ICP-Brasil opens normally. All 8 edge-case tests pass. |

Note: REQUIREMENTS.md traceability table marks INGEST-01 as "Pending" (line 88) while the main list marks it [x] (line 10). This documentation inconsistency was present in the initial verification and remains — it does not affect code correctness.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `backend/api/upload.py` | 15 | `extract_text_with_meta` imported but not called directly — used via orchestrator | Info | Not a bug; orchestrator.run() calls it internally and returns extraction_result; upload.py correctly builds ExtractionMeta from that |
| `backend/services/azure/document_intelligence.py` | 91-99 | Mock path returns static `method="ocr"` always, bypasses adaptive router | Info | Intentional dev mock; does not affect production behavior |

No blocker or warning-level anti-patterns remain.

---

### Human Verification Required

#### 1. Supabase Column Migration

**Test:** Run `ALTER TABLE documents ADD COLUMN IF NOT EXISTS text_extraction_meta JSONB;` against the Supabase database and upload a real PDF.
**Expected:** The document row in Supabase has a non-null `text_extraction_meta` JSON object with `method`, `quality_score`, `library`, `fallback_reason`, and `page_strategies`.
**Why human:** Cannot verify Supabase schema programmatically without live credentials.

#### 2. Native-Text PDF End-to-End

**Test:** Upload a known native-text PDF (e.g., a digitally-created medical report) via `POST /upload` with `USE_MOCK_AZURE=false`.
**Expected:** `result.method == "native"` and `quality_score >= 0.65`; Azure Document Intelligence is NOT called.
**Why human:** Requires a real PDF file, running backend, and real Azure credentials.

---

## Re-verification Summary

The three gaps from the initial verification (2026-04-05T14:30:00Z) are all closed. The Plan 5 worktree commits (c2e3f7b, c506921, e2eac1d) were merged into main via merge commit af9f959.

**Gap 1 — Password protection:** `PasswordProtectedError` class exists at router.py:34. `doc.authenticate("")` is called at router.py:117; raises on failure at router.py:120. `upload.py` imports it at line 17 and catches it with `except PasswordProtectedError` at line 118, raising `HTTPException(status_code=422)` with a Portuguese message. Verified by 2 tests.

**Gap 2 — Corrupt PDF fallback:** `fitz.open()` is wrapped in `try/except Exception` at router.py:100-113. On any open error it logs a warning, calls OCR, and returns `fallback_reason="corrupt_pdf"`. Verified by 1 test.

**Gap 3 — QR code guard:** `_avg_line_length()` helper at router.py:38-43; `_apply_qr_code_guard()` at router.py:46-58; called after page classification at router.py:135. Pages with avg line length > 300 chars have `is_native` set to False. Verified by 2 tests.

**test_edge_cases.py:** 8 tests across all three guard paths plus AcroForm, all passing. Total test suite is now 36 tests (up from 28), all passing in 0.25s.

Plans 1-5 are fully verified. Phase 1 goal is achieved.

---

_Verified: 2026-04-05T15:00:00Z_
_Verifier: Claude (gsd-verifier)_
