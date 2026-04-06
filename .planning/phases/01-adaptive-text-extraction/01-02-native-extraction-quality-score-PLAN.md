---
phase: 01-adaptive-text-extraction
plan: 2
type: execute
wave: 2
depends_on:
  - 01-PLAN-1-page-classifier
files_modified:
  - backend/services/extraction/extractor.py
  - backend/tests/extraction/test_extractor.py
autonomous: true
requirements:
  - INGEST-02
  - INGEST-04

must_haves:
  truths:
    - "extract_text_native() accepts a bytes blob and returns a non-empty string from a real native-text PDF"
    - "compute_quality_score() returns a float in [0.0, 1.0] for any string input including empty string"
    - "Quality score for a well-formed medical text (many words, normal line lengths, some numbers) is ≥ 0.65"
    - "Quality score for random garbage bytes decoded to string is < 0.65"
    - "The four scoring signals use the exact weights: printable_ratio*0.40, word_density*0.35, line_length_score*0.15, numeric_density*0.10"
  artifacts:
    - path: "backend/services/extraction/extractor.py"
      provides: "extract_text_native() and compute_quality_score() functions"
      exports: ["extract_text_native", "compute_quality_score"]
    - path: "backend/tests/extraction/test_extractor.py"
      provides: "Pytest tests for both functions"
  key_links:
    - from: "backend/services/extraction/extractor.py"
      to: "fitz (pymupdf)"
      via: "import fitz"
      pattern: "import fitz"
    - from: "backend/services/extraction/extractor.py"
      to: "backend/services/extraction/classifier.py"
      via: "from services.extraction.classifier import is_native_page"
      pattern: "from services.extraction.classifier import is_native_page"
---

<objective>
Implement `extract_text_native()` (PyMuPDF text extraction per native page) and `compute_quality_score()` (4-signal weighted scorer).

Purpose: These two functions are the core of the adaptive strategy — one extracts text, the other tells us whether to trust it. Both must be correct and tested before the router in Plan 3 can use them.
Output: `services/extraction/extractor.py` with both functions; tests in `tests/extraction/test_extractor.py`.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/research/extraction.md
@backend/services/extraction/classifier.py
</context>

<interfaces>
<!-- Key contracts from Plan 1 that this plan builds on. -->

From backend/services/extraction/classifier.py:
```python
def is_native_page(page) -> dict:
    """
    Returns:
        dict with keys:
          is_native      (bool)
          char_count     (int)
          image_coverage (float)
          has_real_fonts (bool)
    """
```
</interfaces>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Implement extract_text_native()</name>
  <read_first>
    .planning/research/extraction.md
    backend/services/extraction/classifier.py
  </read_first>
  <files>
    backend/services/extraction/extractor.py
  </files>
  <behavior>
    - extract_text_native(file_bytes) where file_bytes is a valid native-text PDF returns a non-empty string
    - Each page's text is separated by a newline
    - Page.get_text("text") is called — NOT get_text("html") or get_text("dict")
    - Pages are processed in order (page 0, page 1, ...)
    - AcroForm widget values are appended to each page's text: page.widgets() is iterated and widget.field_value is collected
    - Only pages classified as native by is_native_page() contribute text (non-native pages yield empty string for that page)
  </behavior>
  <action>
    Create `backend/services/extraction/extractor.py` with `extract_text_native()`:

    ```python
    """
    Native PDF text extraction and quality scoring.

    extract_text_native(): PyMuPDF-based extraction, per-page, with AcroForm support.
    compute_quality_score(): 4-signal weighted quality score [0, 1].
    """
    from __future__ import annotations

    import re
    import string
    import unicodedata


    def extract_text_native(file_bytes: bytes) -> str:
        """
        Extract text from a PDF using PyMuPDF, page by page.

        Only pages classified as native by is_native_page() contribute text.
        AcroForm field values (digital prescriptions, MEMED forms) are collected
        via page.widgets() and appended to the relevant page text.

        Args:
            file_bytes: raw PDF bytes

        Returns:
            Concatenated text from all native pages, pages separated by newline.
        """
        import fitz  # pymupdf — imported here to avoid import error when not installed
        from services.extraction.classifier import is_native_page

        doc = fitz.open(stream=file_bytes, filetype="pdf")
        page_texts: list[str] = []

        for page in doc:
            classification = is_native_page(page)
            if not classification["is_native"]:
                page_texts.append("")
                continue

            # Primary text layer
            page_text = page.get_text("text")

            # AcroForm field values (MEMED digital prescriptions, iClinic forms)
            widget_values: list[str] = []
            try:
                for widget in page.widgets():
                    val = widget.field_value
                    if val and str(val).strip():
                        widget_values.append(str(val).strip())
            except Exception:
                pass  # widgets() may not exist on all page types

            if widget_values:
                page_text = page_text + "\n" + "\n".join(widget_values)

            page_texts.append(page_text)

        doc.close()
        return "\n".join(page_texts)
    ```
  </action>
  <verify>
    <automated>cd backend && python -c "from services.extraction.extractor import extract_text_native; print('ok')"</automated>
  </verify>
  <done>`extract_text_native` is importable. Function body contains `page.get_text("text")` and `page.widgets()`.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Implement compute_quality_score() with tests for both functions</name>
  <read_first>
    .planning/research/extraction.md
    backend/services/extraction/extractor.py
  </read_first>
  <files>
    backend/services/extraction/extractor.py
    backend/tests/extraction/test_extractor.py
  </files>
  <behavior>
    Quality score signals and weights (from research):
    - printable_char_ratio * 0.40: printable chars / total chars (empty string → 0.0)
    - word_density * 0.35: word-like tokens (regex \b[a-zA-ZÀ-ÿ]{2,}\b) / total words, capped at 1.0
    - line_length_score * 0.15: min(avg_line_length / 60.0, 1.0) — normalized to target of 60 chars
    - numeric_density * 0.10: min(numeric_token_count / max(word_count, 1) / 0.15, 1.0) — normalized to 15%
    - Final score = sum of weighted signals, clamped to [0.0, 1.0]

    Test cases:
    - Test 1: empty string → score == 0.0
    - Test 2: well-formed medical text (100+ real words, numbers, avg line ~40 chars) → score >= 0.65
    - Test 3: string of only non-printable chars → score < 0.10
    - Test 4: single very long line (1000 chars, no spaces) → line_length_score component == 1.0, but low word density → overall score reflects that
    - Test 5: score is always in [0.0, 1.0] regardless of input
    - Test 6: weights add up exactly — verify by passing perfect text (all printable, all words, avg 60 chars, 15% numeric) → score == 1.0 (or very close, >= 0.98)
  </behavior>
  <action>
    Append `compute_quality_score()` to `backend/services/extraction/extractor.py`:

    ```python

    def compute_quality_score(text: str) -> float:
        """
        Compute a deterministic quality score for extracted text.

        Four signals combined into a [0, 1] score:
          - Printable char ratio  (weight 0.40): detects corrupt font encodings
          - Word-like token density (weight 0.35): detects garbage encoding
          - Avg line length / 60   (weight 0.15): detects invisible-text artifacts
          - Numeric density / 0.15  (weight 0.10): confirms medical document structure

        Threshold: 0.65 to prefer native over OCR.

        Args:
            text: extracted text string

        Returns:
            float in [0.0, 1.0]
        """
        if not text or not text.strip():
            return 0.0

        # Signal 1: printable character ratio
        total_chars = len(text)
        printable_chars = sum(1 for c in text if c in string.printable or unicodedata.category(c) not in ("Cc", "Cs"))
        printable_ratio = printable_chars / total_chars if total_chars > 0 else 0.0

        # Signal 2: word-like token density
        all_tokens = text.split()
        word_like = re.findall(r"\b[a-zA-ZÀ-ÿ]{2,}\b", text)
        total_tokens = max(len(all_tokens), 1)
        word_density = min(len(word_like) / total_tokens, 1.0)

        # Signal 3: average line length normalized to 60
        lines = [line for line in text.splitlines() if line.strip()]
        avg_line_length = sum(len(line) for line in lines) / max(len(lines), 1)
        line_length_score = min(avg_line_length / 60.0, 1.0)

        # Signal 4: numeric density normalized to 15%
        numeric_tokens = re.findall(r"\b\d+[\.,]?\d*\b", text)
        word_count = max(len(all_tokens), 1)
        numeric_density = min((len(numeric_tokens) / word_count) / 0.15, 1.0)

        score = (
            printable_ratio  * 0.40
            + word_density   * 0.35
            + line_length_score * 0.15
            + numeric_density * 0.10
        )

        return round(min(max(score, 0.0), 1.0), 4)
    ```

    Create `backend/tests/extraction/test_extractor.py`:

    ```python
    """Unit tests for services.extraction.extractor."""
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

    from unittest.mock import MagicMock, patch, PropertyMock
    import pytest
    from services.extraction.extractor import compute_quality_score, extract_text_native


    # ── compute_quality_score tests ───────────────────────────────────────────────

    GOOD_MEDICAL_TEXT = """\
    Paciente apresenta hemoglobina glicada HbA1c de 7.2%, acima do valor de referência 4.0-5.7%.
    Glicemia em jejum: 126 mg/dL. Colesterol total: 198 mg/dL. LDL: 120 mg/dL.
    Triglicérides: 145 mg/dL. Creatinina: 0.9 mg/dL. Ureia: 32 mg/dL.
    Diagnóstico: Diabetes mellitus tipo 2 controlado. Manter metformina 850mg.
    Retorno em 3 meses para novo controle laboratorial. Dr. Carlos Mendes CRM 54321.
    """ * 3


    def test_score_empty_string():
        assert compute_quality_score("") == 0.0


    def test_score_empty_whitespace():
        assert compute_quality_score("   \n\t  ") == 0.0


    def test_score_good_medical_text_above_threshold():
        score = compute_quality_score(GOOD_MEDICAL_TEXT)
        assert score >= 0.65, f"Expected >= 0.65, got {score}"


    def test_score_non_printable_chars():
        garbage = "\x00\x01\x02\x03\x04\x05" * 50
        score = compute_quality_score(garbage)
        assert score < 0.10, f"Expected < 0.10 for garbage, got {score}"


    def test_score_always_in_range():
        for text in ["", "abc", GOOD_MEDICAL_TEXT, "\xff" * 100, "123 456 789"]:
            score = compute_quality_score(text)
            assert 0.0 <= score <= 1.0, f"Score {score} out of [0, 1] for input {repr(text[:30])}"


    def test_score_perfect_text_near_one():
        # Construct text with ~15% numeric density, real words, avg line ~60 chars
        line = "Hemoglobina glicada 7.2 mg dL colesterol triglicerides 145 creatinina 0.9"
        perfect = (line + "\n") * 20
        score = compute_quality_score(perfect)
        assert score >= 0.85, f"Expected >= 0.85 for perfect text, got {score}"


    # ── extract_text_native tests ─────────────────────────────────────────────────

    def _make_mock_doc(pages_config):
        """
        Build a mock fitz document.
        pages_config: list of dicts with keys: text (str), is_native (bool), widgets (list of str)
        """
        import fitz

        mock_pages = []
        for cfg in pages_config:
            page = MagicMock()
            page.get_text.return_value = cfg.get("text", "")
            page.get_fonts.return_value = [("x", "T1", "T1", "Helvetica", "Helvetica", "Win", 0)]
            page.rect.width = 595.0
            page.rect.height = 842.0
            page.get_image_info.return_value = []

            # is_native_page reads get_text with "text" and "dict"
            text_val = cfg.get("text", "")

            def make_get_text(t, native):
                def get_text(mode="text"):
                    if mode == "text":
                        return t
                    return {"blocks": [{"lines": [{"spans": [{"font": "Helvetica", "size": 12 if native else 0, "text": t}]}]}]}
                return get_text

            page.get_text.side_effect = make_get_text(text_val, cfg.get("is_native", True))

            widget_mocks = []
            for wval in cfg.get("widgets", []):
                w = MagicMock()
                w.field_value = wval
                widget_mocks.append(w)
            page.widgets.return_value = iter(widget_mocks)
            mock_pages.append(page)

        mock_doc = MagicMock()
        mock_doc.__iter__ = MagicMock(return_value=iter(mock_pages))
        mock_doc.close = MagicMock()
        return mock_doc


    def test_extract_native_single_native_page():
        with patch("services.extraction.extractor.fitz") as mock_fitz, \
             patch("services.extraction.extractor.is_native_page") as mock_classify:
            mock_classify.return_value = {"is_native": True, "char_count": 100, "image_coverage": 0.05, "has_real_fonts": True}
            mock_page = MagicMock()
            mock_page.get_text.return_value = "Resultado do exame laboratorial"
            mock_page.widgets.return_value = []
            mock_doc = MagicMock()
            mock_doc.__iter__ = MagicMock(return_value=iter([mock_page]))
            mock_doc.close = MagicMock()
            mock_fitz.open.return_value = mock_doc

            result = extract_text_native(b"%PDF-1.4 fake")
            assert "Resultado do exame laboratorial" in result


    def test_extract_native_skips_non_native_pages():
        with patch("services.extraction.extractor.fitz") as mock_fitz, \
             patch("services.extraction.extractor.is_native_page") as mock_classify:
            mock_classify.side_effect = [
                {"is_native": True, "char_count": 100, "image_coverage": 0.05, "has_real_fonts": True},
                {"is_native": False, "char_count": 10, "image_coverage": 0.80, "has_real_fonts": False},
            ]
            page1, page2 = MagicMock(), MagicMock()
            page1.get_text.return_value = "Native content here"
            page1.widgets.return_value = []
            page2.get_text.return_value = "Should be skipped"
            page2.widgets.return_value = []

            mock_doc = MagicMock()
            mock_doc.__iter__ = MagicMock(return_value=iter([page1, page2]))
            mock_doc.close = MagicMock()
            mock_fitz.open.return_value = mock_doc

            result = extract_text_native(b"%PDF-1.4 fake")
            assert "Native content here" in result
            assert "Should be skipped" not in result


    def test_extract_native_appends_widget_values():
        with patch("services.extraction.extractor.fitz") as mock_fitz, \
             patch("services.extraction.extractor.is_native_page") as mock_classify:
            mock_classify.return_value = {"is_native": True, "char_count": 100, "image_coverage": 0.05, "has_real_fonts": True}
            widget = MagicMock()
            widget.field_value = "Metformina 850mg"
            mock_page = MagicMock()
            mock_page.get_text.return_value = "Prescrição médica"
            mock_page.widgets.return_value = [widget]
            mock_doc = MagicMock()
            mock_doc.__iter__ = MagicMock(return_value=iter([mock_page]))
            mock_doc.close = MagicMock()
            mock_fitz.open.return_value = mock_doc

            result = extract_text_native(b"%PDF-1.4 fake")
            assert "Metformina 850mg" in result
    ```
  </action>
  <verify>
    <automated>cd backend && python -m pytest tests/extraction/test_extractor.py -v 2>&1</automated>
  </verify>
  <done>All tests pass. `compute_quality_score` is importable and returns float in [0, 1]. `extract_text_native` is importable.</done>
</task>

</tasks>

<verification>
- `backend/services/extraction/extractor.py` contains `def extract_text_native(` and `def compute_quality_score(`
- `cd backend && python -m pytest tests/extraction/test_extractor.py -v` exits 0
- `compute_quality_score("")` returns `0.0`
- `compute_quality_score` uses weights: `0.40`, `0.35`, `0.15`, `0.10` (grep confirms)
- `extract_text_native` calls `page.widgets()` (grep confirms)
</verification>

<success_criteria>
- `extract_text_native(file_bytes)` extracts text from all native pages, appends widget values, returns joined string
- `compute_quality_score(text)` returns float in [0.0, 1.0] using the exact 4-signal weighted formula from research
- Quality threshold 0.65 is meaningful: good medical text scores ≥ 0.65, garbage scores < 0.10
- All tests pass
</success_criteria>

<output>
After completion, create `.planning/phases/01-adaptive-text-extraction/01-2-SUMMARY.md`
</output>
