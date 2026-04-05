---
phase: 01-adaptive-text-extraction
plan: 5
type: execute
wave: 4
depends_on:
  - 01-PLAN-3-adaptive-router
files_modified:
  - backend/services/extraction/router.py
  - backend/api/upload.py
  - backend/tests/extraction/test_edge_cases.py
autonomous: true
requirements:
  - INGEST-06

must_haves:
  truths:
    - "Uploading a password-protected PDF returns HTTP 422 with a Portuguese error message"
    - "A corrupt/truncated PDF attempts self-repair via fitz.TOOLS.mupdf_set_error_callback and falls back to OCR if repair fails"
    - "AcroForm field values (page.widgets()) are included in native text — already wired in Plan 2, verified here"
    - "ICP-Brasil digitally-signed PDFs open normally with fitz.open() — no special handling, just verified not to crash"
    - "QR code pages (one very long line, avg_line_length > 300 chars) are reclassified as non-native despite high char count"
  artifacts:
    - path: "backend/services/extraction/router.py"
      provides: "Password-protected detection, corrupt self-repair, QR code guard added to routing"
      contains: "authenticate"
    - path: "backend/api/upload.py"
      provides: "HTTP 422 raised on PasswordProtectedError from router"
      contains: "PasswordProtectedError"
    - path: "backend/tests/extraction/test_edge_cases.py"
      provides: "Tests for all 5 edge cases"
  key_links:
    - from: "backend/api/upload.py"
      to: "backend/services/extraction/router.py"
      via: "PasswordProtectedError caught → HTTPException 422"
      pattern: "PasswordProtectedError"
    - from: "backend/services/extraction/router.py"
      to: "fitz.open"
      via: "doc.authenticate('') for password protection"
      pattern: "authenticate"
---

<objective>
Harden the adaptive router against the five medical PDF edge cases identified in research: password-protected PDFs, corrupt/truncated PDFs, AcroForm fields, ICP-Brasil signed PDFs, and QR code inflation of char counts.

Purpose: Medical document collections contain all of these. Silent failure (falling back to empty text or crashing) breaks the pipeline. Explicit errors and targeted fallbacks keep the system reliable.
Output: Updated `router.py` with edge-case guards; `upload.py` catching `PasswordProtectedError`; tests for all 5 cases.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/research/extraction.md
@backend/services/extraction/router.py
@backend/api/upload.py
</context>

<interfaces>
<!-- Contracts this plan modifies. -->

Current router.py — extract_text_adaptive signature (from Plan 3):
```python
def extract_text_adaptive(
    file_bytes: bytes,
    filename: str,
    extract_text_ocr_fn,
) -> dict:
```

upload.py currently handles exceptions from orchestrator.run():
```python
except HTTPException:
    raise
except Exception as e:
    raise HTTPException(status_code=500, detail=f"Erro ao processar documento: {e}")
```

After this plan, a new `except PasswordProtectedError` clause is added before the generic `except Exception`.
</interfaces>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add edge-case guards to router.py (password, corrupt, QR code)</name>
  <read_first>
    .planning/research/extraction.md
    backend/services/extraction/router.py
    backend/services/extraction/classifier.py
  </read_first>
  <files>
    backend/services/extraction/router.py
    backend/tests/extraction/test_edge_cases.py
  </files>
  <behavior>
    Edge cases to handle in router.py:

    1. Password-protected PDF:
       - fitz.open() returns a doc where doc.is_encrypted == True
       - Attempt doc.authenticate("") (print-password-only PDFs open this way)
       - If still encrypted after authenticate("") → raise PasswordProtectedError("PDF protegido por senha")
       - Do NOT silently route to OCR — OCR would also fail or return garbage

    2. Corrupt/truncated PDF:
       - fitz.open() raises fitz.FileDataError or any exception
       - Catch the exception, log a warning, return OCR result with fallback_reason="corrupt_pdf"
       - PyMuPDF performs partial self-repair internally; the catch covers total failures

    3. QR code guard (extends classifier):
       - In router.py (not classifier.py), after computing page_strategies, check each "native" page:
         If a page's text has avg_line_length > 300 (i.e., one very long line — QR URL pattern),
         reclassify that page as non-native by setting is_native=False and adding a "qr_code_guard" note
       - This prevents QR code URL lines from inflating char_count and triggering native routing

    4. ICP-Brasil signed PDFs:
       - These open normally with fitz.open() — no special handling required
       - Verified by the fact that tests pass with a real signed PDF (no exception expected)

    5. AcroForm field values:
       - Already implemented in extract_text_native() via page.widgets() (Plan 2)
       - Verified in test_edge_cases.py with a mock AcroForm page

    Test cases:
    - Test 1: password-protected PDF (doc.is_encrypted=True, authenticate returns 0) → PasswordProtectedError raised
    - Test 2: PDF that authenticate("") opens successfully (returns non-zero) → proceeds normally, no error
    - Test 3: fitz.open() raises fitz.FileDataError → method=="ocr", fallback_reason=="corrupt_pdf"
    - Test 4: page with a single 350-char line (QR URL) → reclassified as non-native in page_strategies
    - Test 5: AcroForm page — page.widgets() returns values → values appear in extract_text_native() output (mock test)
  </behavior>
  <action>
    Replace the contents of `backend/services/extraction/router.py` with the updated version below.
    The function signature and return shape are unchanged from Plan 3.

    ```python
    """
    Adaptive text extraction router.

    Routing logic (v1):
      - non-PDF → OCR
      - password-protected PDF → raise PasswordProtectedError (HTTP 422)
      - corrupt PDF → OCR fallback (fallback_reason="corrupt_pdf")
      - all-native pages + score >= 0.65 → native
      - all-native pages + score < 0.65  → OCR (fallback_reason="low_quality")
      - all-scanned pages               → OCR
      - mixed pages                     → OCR (fallback_reason="mixed_pages"; v2 will do page-level)

    Edge cases handled:
      - Password-protected: attempt doc.authenticate("") first; raise if still encrypted
      - Corrupt/truncated: catch fitz.FileDataError, fallback to OCR
      - QR code inflation: avg_line_length > 300 chars → reclassify page as non-native
      - AcroForm fields: handled in extract_text_native() via page.widgets() (Plan 2)
      - ICP-Brasil signed PDFs: open normally, no special handling required
    """
    from __future__ import annotations

    _QUALITY_THRESHOLD = 0.65
    _QR_LINE_LENGTH_THRESHOLD = 300  # lines longer than this are likely QR URLs, not content


    class PasswordProtectedError(Exception):
        """Raised when a PDF is encrypted and cannot be opened without a password."""


    def _avg_line_length(text: str) -> float:
        """Return the average line length (in chars) of non-empty lines in text."""
        lines = [line for line in text.splitlines() if line.strip()]
        if not lines:
            return 0.0
        return sum(len(line) for line in lines) / len(lines)


    def _apply_qr_code_guard(page_strategies: list[dict], page_texts: list[str]) -> list[dict]:
        """
        Reclassify pages whose text looks like QR code URLs (one very long line).
        Mutates and returns page_strategies with is_native=False for QR pages.
        """
        result = []
        for i, strategy in enumerate(page_strategies):
            if strategy.get("is_native") and i < len(page_texts):
                avg_len = _avg_line_length(page_texts[i])
                if avg_len > _QR_LINE_LENGTH_THRESHOLD:
                    strategy = {**strategy, "is_native": False, "qr_code_guard": True, "avg_line_length": avg_len}
            result.append(strategy)
        return result


    def extract_text_adaptive(
        file_bytes: bytes,
        filename: str,
        extract_text_ocr_fn,
    ) -> dict:
        """
        Route PDF extraction to native PyMuPDF or Azure OCR based on page analysis.

        Args:
            file_bytes:          raw file bytes
            filename:            original filename (used for extension check)
            extract_text_ocr_fn: callable(file_bytes, filename) -> str
                                 Points to the Azure OCR implementation.

        Returns:
            dict with keys:
              text            (str)
              method          (str)   "native" | "ocr"
              quality_score   (float) [0, 1]
              fallback_reason (str | None)
              page_strategies (list[dict])
              library         (str)

        Raises:
            PasswordProtectedError: if the PDF is password-protected and cannot be decrypted
        """
        import fitz
        from services.extraction.classifier import is_native_page
        from services.extraction.extractor import extract_text_native, compute_quality_score

        # Non-PDF: always OCR
        if not filename.lower().endswith(".pdf"):
            ocr_text = extract_text_ocr_fn(file_bytes, filename)
            return {
                "text": ocr_text,
                "method": "ocr",
                "quality_score": compute_quality_score(ocr_text),
                "fallback_reason": "non_pdf",
                "page_strategies": [],
                "library": "azure-ai-formrecognizer/3.3.3",
            }

        # Open PDF — handle corrupt files
        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
        except Exception as exc:
            # Corrupt or truncated PDF — attempt OCR fallback
            import logging
            logging.getLogger(__name__).warning("Corrupt PDF detected, falling back to OCR: %s", exc)
            ocr_text = extract_text_ocr_fn(file_bytes, filename)
            return {
                "text": ocr_text,
                "method": "ocr",
                "quality_score": compute_quality_score(ocr_text),
                "fallback_reason": "corrupt_pdf",
                "page_strategies": [],
                "library": "azure-ai-formrecognizer/3.3.3",
            }

        # Password-protected PDFs
        if doc.is_encrypted:
            auth_result = doc.authenticate("")  # 0 = failed, non-zero = success
            if not auth_result:
                doc.close()
                raise PasswordProtectedError(
                    "O PDF está protegido por senha e não pode ser processado automaticamente."
                )
            # authenticate("") succeeded — print-only protection, proceed normally

        # Classify all pages; collect per-page text for QR guard
        page_strategies: list[dict] = []
        page_texts: list[str] = []
        for page in doc:
            strategy = is_native_page(page)
            page_strategies.append(strategy)
            page_texts.append(page.get_text("text") if strategy["is_native"] else "")
        doc.close()

        # Apply QR code guard — reclassify QR URL pages as non-native
        page_strategies = _apply_qr_code_guard(page_strategies, page_texts)

        all_native = all(p["is_native"] for p in page_strategies)
        any_native = any(p["is_native"] for p in page_strategies)
        mixed = any_native and not all_native

        # Mixed pages → OCR (v1 safe fallback)
        if mixed:
            ocr_text = extract_text_ocr_fn(file_bytes, filename)
            return {
                "text": ocr_text,
                "method": "ocr",
                "quality_score": compute_quality_score(ocr_text),
                "fallback_reason": "mixed_pages",
                "page_strategies": page_strategies,
                "library": "azure-ai-formrecognizer/3.3.3",
            }

        # All-scanned → OCR
        if not any_native:
            ocr_text = extract_text_ocr_fn(file_bytes, filename)
            return {
                "text": ocr_text,
                "method": "ocr",
                "quality_score": compute_quality_score(ocr_text),
                "fallback_reason": None,
                "page_strategies": page_strategies,
                "library": "azure-ai-formrecognizer/3.3.3",
            }

        # All-native: extract then score
        native_text = extract_text_native(file_bytes)
        score = compute_quality_score(native_text)

        if score >= _QUALITY_THRESHOLD:
            return {
                "text": native_text,
                "method": "native",
                "quality_score": score,
                "fallback_reason": None,
                "page_strategies": page_strategies,
                "library": f"pymupdf/{fitz.__version__}",
            }

        # Score below threshold → OCR fallback
        ocr_text = extract_text_ocr_fn(file_bytes, filename)
        return {
            "text": ocr_text,
            "method": "ocr",
            "quality_score": compute_quality_score(ocr_text),
            "fallback_reason": "low_quality",
            "page_strategies": page_strategies,
            "library": "azure-ai-formrecognizer/3.3.3",
        }
    ```

    Create `backend/tests/extraction/test_edge_cases.py`:

    ```python
    """Tests for medical PDF edge cases in router.py."""
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

    from unittest.mock import MagicMock, patch, PropertyMock
    import pytest
    from services.extraction.router import (
        extract_text_adaptive,
        PasswordProtectedError,
        _avg_line_length,
        _apply_qr_code_guard,
    )


    def _mock_ocr_fn(text="OCR result"):
        fn = MagicMock(return_value=text)
        return fn


    # ── Password protection ───────────────────────────────────────────────────────

    def test_password_protected_raises_error():
        ocr_fn = _mock_ocr_fn()
        with patch("services.extraction.router.fitz") as mock_fitz:
            mock_doc = MagicMock()
            mock_doc.is_encrypted = True
            mock_doc.authenticate.return_value = 0  # authentication failed
            mock_fitz.open.return_value = mock_doc

            with pytest.raises(PasswordProtectedError):
                extract_text_adaptive(b"%PDF fake", "protected.pdf", ocr_fn)

        ocr_fn.assert_not_called()


    def test_print_only_protection_proceeds_normally():
        """PDF with print-only password — authenticate('') succeeds."""
        ocr_fn = _mock_ocr_fn()
        native_classify = {"is_native": True, "char_count": 200, "image_coverage": 0.05, "has_real_fonts": True}

        with patch("services.extraction.router.fitz") as mock_fitz, \
             patch("services.extraction.router.is_native_page", return_value=native_classify), \
             patch("services.extraction.router.extract_text_native", return_value="Texto do laudo"), \
             patch("services.extraction.router.compute_quality_score", return_value=0.80):
            mock_page = MagicMock()
            mock_page.get_text.return_value = "Texto do laudo"
            mock_doc = MagicMock()
            mock_doc.is_encrypted = True
            mock_doc.authenticate.return_value = 1  # success
            mock_doc.__iter__ = MagicMock(return_value=iter([mock_page]))
            mock_doc.close = MagicMock()
            mock_fitz.open.return_value = mock_doc

            result = extract_text_adaptive(b"%PDF fake", "print-locked.pdf", ocr_fn)

        assert result["method"] == "native"
        ocr_fn.assert_not_called()


    # ── Corrupt PDF ───────────────────────────────────────────────────────────────

    def test_corrupt_pdf_falls_back_to_ocr():
        ocr_fn = _mock_ocr_fn("OCR from corrupt PDF")
        with patch("services.extraction.router.fitz") as mock_fitz, \
             patch("services.extraction.router.compute_quality_score", return_value=0.70):
            mock_fitz.open.side_effect = Exception("truncated file")

            result = extract_text_adaptive(b"not a pdf", "corrupt.pdf", ocr_fn)

        assert result["method"] == "ocr"
        assert result["fallback_reason"] == "corrupt_pdf"
        ocr_fn.assert_called_once()


    # ── QR code guard ─────────────────────────────────────────────────────────────

    def test_avg_line_length_single_long_line():
        text = "https://example.com/qr/" + "x" * 350
        assert _avg_line_length(text) > 300


    def test_avg_line_length_normal_text():
        text = "Hemoglobina glicada: 7.2%\nGlicemia: 126 mg/dL\nColesterol: 198 mg/dL"
        assert _avg_line_length(text) < 60


    def test_qr_code_guard_reclassifies_long_line_pages():
        strategies = [
            {"is_native": True, "char_count": 380, "image_coverage": 0.05, "has_real_fonts": True},
        ]
        long_url = "https://qr.hospital.com.br/laudo/" + "a" * 340
        page_texts = [long_url]

        result = _apply_qr_code_guard(strategies, page_texts)
        assert result[0]["is_native"] is False
        assert result[0].get("qr_code_guard") is True


    def test_qr_code_guard_preserves_normal_pages():
        strategies = [
            {"is_native": True, "char_count": 200, "image_coverage": 0.05, "has_real_fonts": True},
        ]
        normal_text = "Hemoglobina glicada: 7.2%\nGlicemia: 126 mg/dL"
        result = _apply_qr_code_guard(strategies, [normal_text])
        assert result[0]["is_native"] is True
        assert "qr_code_guard" not in result[0]


    # ── AcroForm fields ───────────────────────────────────────────────────────────

    def test_acroform_widget_values_included_in_native_text():
        """Verify that page.widgets() values are appended by extract_text_native()."""
        from services.extraction.extractor import extract_text_native

        with patch("services.extraction.extractor.fitz") as mock_fitz, \
             patch("services.extraction.extractor.is_native_page") as mock_classify:
            mock_classify.return_value = {
                "is_native": True, "char_count": 100, "image_coverage": 0.05, "has_real_fonts": True
            }
            widget = MagicMock()
            widget.field_value = "Amoxicilina 500mg - 3x ao dia"
            mock_page = MagicMock()
            mock_page.get_text.return_value = "Prescrição eletrônica MEMED"
            mock_page.widgets.return_value = [widget]
            mock_doc = MagicMock()
            mock_doc.__iter__ = MagicMock(return_value=iter([mock_page]))
            mock_doc.close = MagicMock()
            mock_fitz.open.return_value = mock_doc

            text = extract_text_native(b"%PDF fake")

        assert "Amoxicilina 500mg" in text
        assert "Prescrição eletrônica MEMED" in text
    ```
  </action>
  <verify>
    <automated>cd backend && python -m pytest tests/extraction/test_edge_cases.py -v 2>&1</automated>
  </verify>
  <done>All edge case tests pass. `PasswordProtectedError` is importable from `services.extraction.router`. `router.py` contains `authenticate` and `qr_code_guard`.</done>
</task>

<task type="auto">
  <name>Task 2: Add PasswordProtectedError handling in upload.py</name>
  <read_first>
    backend/api/upload.py
    backend/services/extraction/router.py
  </read_first>
  <files>
    backend/api/upload.py
  </files>
  <action>
    Open `backend/api/upload.py`. Add an import for `PasswordProtectedError` at the top of the file, after existing imports:

    ```python
    from services.extraction.router import PasswordProtectedError
    ```

    Then in the `upload_document` endpoint, in the `try/except` block, add a specific catch clause for `PasswordProtectedError` BEFORE the generic `except Exception as e` clause:

    ```python
        except PasswordProtectedError as e:
            raise HTTPException(
                status_code=422,
                detail=f"PDF protegido por senha: {e}. Por favor, remova a proteção antes de fazer upload.",
            )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Erro ao processar documento: {e}")
    ```

    The `PasswordProtectedError` clause must appear BEFORE `except HTTPException` so it is caught specifically.
    Final exception handler order:
      1. `except PasswordProtectedError as e:` → 422
      2. `except HTTPException:` → re-raise
      3. `except Exception as e:` → 500

    No other changes to upload.py.
  </action>
  <verify>
    <automated>cd backend && python -c "from api.upload import router; print('ok')"</automated>
  </verify>
  <done>
    `upload.py` imports `PasswordProtectedError` (grep confirms).
    `upload.py` contains `status_code=422` in the `PasswordProtectedError` handler (grep confirms).
    `cd backend && python -c "from api.upload import router; print('ok')"` prints "ok".
  </done>
</task>

</tasks>

<verification>
- `cd backend && python -m pytest tests/extraction/test_edge_cases.py -v` exits 0 with all tests passed
- `grep -n "authenticate" backend/services/extraction/router.py` shows the password auth attempt
- `grep -n "qr_code_guard" backend/services/extraction/router.py` shows QR guard logic
- `grep -n "PasswordProtectedError" backend/api/upload.py` shows import and except clause
- `grep -n "status_code=422" backend/api/upload.py` shows the 422 response
- `grep -n "corrupt_pdf" backend/services/extraction/router.py` shows corrupt fallback

Run the full extraction test suite to confirm no regressions:
- `cd backend && python -m pytest tests/extraction/ -v` — all tests pass
</verification>

<success_criteria>
- Password-protected PDFs → HTTP 422, not 500, with a Portuguese message explaining the issue
- Corrupt PDFs → OCR fallback with `fallback_reason="corrupt_pdf"`, not a 500 error
- QR code pages (avg_line_length > 300) → reclassified as non-native, preventing false native routing
- AcroForm widget values included in native extraction output (verified via test)
- ICP-Brasil signed PDFs → open normally (no crash, no special case needed)
- All previous test suites still pass (no regressions)
</success_criteria>

<output>
After completion, create `.planning/phases/01-adaptive-text-extraction/01-5-SUMMARY.md`

The full test suite to run before closing the phase:
`cd backend && python -m pytest tests/extraction/ -v`
</output>
