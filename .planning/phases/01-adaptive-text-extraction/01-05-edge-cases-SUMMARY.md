---
phase: 01-adaptive-text-extraction
plan: 5
subsystem: extraction
tags: [edge-cases, pdf, password-protection, corrupt-pdf, qr-code, acroform, router]
dependency_graph:
  requires: [01-01-page-classifier, 01-02-native-extraction-quality-score, 01-03-adaptive-router]
  provides: [hardened-router, password-protected-422, corrupt-pdf-fallback, qr-code-guard]
  affects: [backend/api/upload.py, backend/services/extraction/router.py]
tech_stack:
  added: []
  patterns: [PasswordProtectedError exception hierarchy, QR code heuristic via avg_line_length]
key_files:
  created:
    - backend/services/extraction/router.py
    - backend/tests/extraction/test_edge_cases.py
    - backend/services/extraction/classifier.py
    - backend/services/extraction/extractor.py
  modified:
    - backend/api/upload.py
decisions:
  - "fitz and other imports moved to module level in router.py to support test patching via unittest.mock"
  - "mock_fitz.__version__ must be explicitly set in tests that reach the native return branch"
metrics:
  duration: 8min
  completed_date: "2026-04-05"
  tasks_completed: 2
  files_changed: 6
requirements: [INGEST-06]
---

# Phase 01 Plan 05: Edge Cases Summary

**One-liner:** Hardened adaptive router with password-protected (HTTP 422), corrupt-PDF (OCR fallback), and QR-code-inflation guards; 8 tests passing.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add edge-case guards to router.py (password, corrupt, QR) | c506921 | backend/services/extraction/router.py, backend/tests/extraction/test_edge_cases.py |
| 2 | Add PasswordProtectedError handling in upload.py | e2eac1d | backend/api/upload.py |

## What Was Built

### Task 1 — router.py edge-case hardening

`backend/services/extraction/router.py` now handles five medical PDF edge cases:

1. **Password-protected PDF:** `doc.authenticate("")` attempted; if still encrypted, raises `PasswordProtectedError("O PDF está protegido por senha...")`. OCR is never called — it would return garbage.
2. **Corrupt/truncated PDF:** `fitz.open()` exception caught, warning logged, OCR fallback with `fallback_reason="corrupt_pdf"`.
3. **QR code inflation:** `_apply_qr_code_guard()` reclassifies pages where `avg_line_length > 300` as non-native — prevents QR URL lines from inflating char counts and triggering false native routing.
4. **ICP-Brasil signed PDFs:** No special handling needed — `fitz.open()` handles these transparently.
5. **AcroForm fields:** Already implemented in `extract_text_native()` via `page.widgets()` (Plan 2); verified by test.

New module-level exports: `PasswordProtectedError`, `_avg_line_length`, `_apply_qr_code_guard`.

### Task 2 — upload.py error handling

`backend/api/upload.py` now imports `PasswordProtectedError` and catches it before the generic `except Exception` handler, returning HTTP 422 with a Portuguese-language message:

```
PDF protegido por senha: <message>. Por favor, remova a proteção antes de fazer upload.
```

Exception handler order:
1. `except PasswordProtectedError` → 422
2. `except HTTPException` → re-raise
3. `except Exception` → 500

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] fitz imported at module level instead of inside function**
- **Found during:** Task 1 verification (tests failed with `AttributeError: module has no attribute 'fitz'`)
- **Issue:** Plan specified `import fitz` inside `extract_text_adaptive()` function, but `unittest.mock.patch("services.extraction.router.fitz")` requires the name to exist at module scope at import time.
- **Fix:** Moved `import fitz`, `from services.extraction.classifier import is_native_page`, and `from services.extraction.extractor import ...` to module level; also extracted `logging.getLogger(__name__)` to module-level `_logger`.
- **Files modified:** `backend/services/extraction/router.py`
- **Commit:** c506921

**2. [Rule 1 - Bug] Mock fitz missing `__version__` attribute**
- **Found during:** Task 1 (test_print_only_protection_proceeds_normally)
- **Issue:** Test patching `fitz` as a MagicMock fails when router returns `f"pymupdf/{fitz.__version__}"` because magic attributes raise `AttributeError` on MagicMock.
- **Fix:** Added `mock_fitz.__version__ = "1.23.0"` in the relevant test case.
- **Files modified:** `backend/tests/extraction/test_edge_cases.py`
- **Commit:** c506921

## Verification Results

```
cd backend && python -m pytest tests/extraction/ -v
8 passed in 0.11s
```

All plan verification checks confirmed:
- `grep "authenticate" backend/services/extraction/router.py` — found (line 117)
- `grep "qr_code_guard" backend/services/extraction/router.py` — found (line 56, 135)
- `grep "PasswordProtectedError" backend/api/upload.py` — found (import + except clause)
- `grep "status_code=422" backend/api/upload.py` — found (line 106)
- `grep "corrupt_pdf" backend/services/extraction/router.py` — found (line 110)

## Known Stubs

None — all edge-case handlers are fully wired. The PasswordProtectedError flows from router.py through upload.py to the HTTP response. The QR guard and corrupt fallback are fully functional.

## Self-Check: PASSED

Files created/exist:
- `backend/services/extraction/router.py` — FOUND
- `backend/tests/extraction/test_edge_cases.py` — FOUND
- `backend/api/upload.py` — FOUND (modified)

Commits exist:
- c2e3f7b (test RED phase) — FOUND
- c506921 (feat GREEN phase) — FOUND
- e2eac1d (feat upload.py) — FOUND
