---
phase: 01-adaptive-text-extraction
plan: 1
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/requirements.txt
  - backend/services/extraction/__init__.py
  - backend/services/extraction/classifier.py
  - backend/tests/extraction/test_classifier.py
autonomous: true
requirements:
  - INGEST-01

must_haves:
  truths:
    - "A page with ≥50 printable chars, <60% image coverage, and at least one real font is classified as native"
    - "A blank or image-only page is classified as non-native"
    - "A page whose only font is GlyphLessFont or size-0 is classified as non-native despite char count"
    - "The classifier accepts a fitz.Page object and returns a dict with is_native, char_count, image_coverage, has_real_fonts"
  artifacts:
    - path: "backend/requirements.txt"
      provides: "pymupdf dependency declared"
      contains: "pymupdf"
    - path: "backend/services/extraction/__init__.py"
      provides: "Package marker"
    - path: "backend/services/extraction/classifier.py"
      provides: "is_native_page() function"
      exports: ["is_native_page"]
    - path: "backend/tests/extraction/test_classifier.py"
      provides: "Pytest tests for classifier"
  key_links:
    - from: "backend/services/extraction/classifier.py"
      to: "fitz (pymupdf)"
      via: "import fitz"
      pattern: "import fitz"
    - from: "backend/tests/extraction/test_classifier.py"
      to: "backend/services/extraction/classifier.py"
      via: "from services.extraction.classifier import is_native_page"
      pattern: "from services.extraction.classifier import is_native_page"
---

<objective>
Add pymupdf to the dependency list and implement the per-page native-text classifier that all later plans depend on.

Purpose: Every routing decision in this phase starts with "is this page native?" — that question must be answered by a correct, tested function before any downstream code is written.
Output: `pymupdf` in requirements.txt, `services/extraction/` package, `is_native_page()` classifier with passing tests.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/ROADMAP.md
@.planning/research/extraction.md
@.planning/codebase/STACK.md
@backend/requirements.txt
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add pymupdf and create services/extraction package</name>
  <read_first>
    backend/requirements.txt
  </read_first>
  <files>
    backend/requirements.txt
    backend/services/extraction/__init__.py
  </files>
  <behavior>
    - After adding pymupdf: `import fitz; fitz.open()` runs without ImportError
    - `backend/services/extraction/__init__.py` exists and is importable as a package
  </behavior>
  <action>
    1. Open `backend/requirements.txt`. After the `# QR Code e PDF` section append:

       ```
       # PDF native extraction
       pymupdf==1.24.5
       ```

       Use exactly `pymupdf==1.24.5` (latest stable as of research; do NOT use the `fitz` package name — that is a different, unmaintained package).

    2. Create directory `backend/services/extraction/` if it does not exist.

    3. Create `backend/services/extraction/__init__.py` as an empty file (just a newline). This makes the directory a Python package.

    4. Install the dependency locally: `pip install pymupdf==1.24.5` so tests can run.
  </action>
  <verify>
    <automated>cd backend && python -c "import fitz; print(fitz.__version__)"</automated>
  </verify>
  <done>Command prints a version string (e.g. "1.24.5") without error. requirements.txt contains "pymupdf==1.24.5".</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Implement is_native_page() classifier with tests</name>
  <read_first>
    .planning/research/extraction.md
    backend/services/extraction/__init__.py
  </read_first>
  <files>
    backend/services/extraction/classifier.py
    backend/tests/extraction/__init__.py
    backend/tests/extraction/test_classifier.py
  </files>
  <behavior>
    - Test 1 (native page): page with 100 chars, 10% image coverage, font "Helvetica" size 12 → is_native=True
    - Test 2 (too few chars): page with 30 chars, 5% image coverage, real font → is_native=False
    - Test 3 (image dominant): page with 200 chars, 70% image coverage, real font → is_native=False
    - Test 4 (GlyphLessFont only): page with 200 chars, 5% image coverage, font "GlyphLessFont" → is_native=False
    - Test 5 (size-0 font): page with 200 chars, 5% image coverage, font "SomeFont" size 0 → is_native=False
    - Test 6 (mixed fonts): page with 200 chars, 5% image coverage, one real font + one GlyphLessFont → is_native=True (has at least one real font)
    - Return dict always includes keys: is_native (bool), char_count (int), image_coverage (float 0.0–1.0), has_real_fonts (bool)
  </behavior>
  <action>
    Create `backend/services/extraction/classifier.py` with the following implementation:

    ```python
    """
    Per-page native text classifier for adaptive PDF extraction.

    A page is "native" (contains extractable text) when ALL three conditions hold:
      1. char_count >= 50    — enough text to be meaningful
      2. image_coverage < 0.60  — not dominated by raster images
      3. has_real_fonts == True  — at least one non-artifact font present

    Returns a dict, not a dataclass, to avoid circular import with the orchestrator.
    """
    from __future__ import annotations

    _FAKE_FONTS = {"GlyphLessFont"}
    _CHAR_THRESHOLD = 50
    _IMAGE_COVERAGE_THRESHOLD = 0.60


    def is_native_page(page) -> dict:
        """
        Classify a single fitz.Page as native-text or image/artifact.

        Args:
            page: fitz.Page object from an open fitz.Document

        Returns:
            dict with keys:
              is_native      (bool)
              char_count     (int)
              image_coverage (float)  — fraction of page area covered by images [0.0, 1.0]
              has_real_fonts (bool)
        """
        # Signal 1: character count
        text = page.get_text("text")
        char_count = len(text.strip())

        # Signal 2: image coverage ratio
        page_area = page.rect.width * page.rect.height
        if page_area == 0:
            image_coverage = 1.0
        else:
            image_area = sum(
                abs(img["width"] * img["height"])
                for img in page.get_image_info()
            )
            image_coverage = min(image_area / page_area, 1.0)

        # Signal 3: font sanity — reject pages whose ONLY fonts are GlyphLessFont or size-0
        has_real_fonts = _has_real_fonts(page)

        is_native = (
            char_count >= _CHAR_THRESHOLD
            and image_coverage < _IMAGE_COVERAGE_THRESHOLD
            and has_real_fonts
        )

        return {
            "is_native": is_native,
            "char_count": char_count,
            "image_coverage": image_coverage,
            "has_real_fonts": has_real_fonts,
        }


    def _has_real_fonts(page) -> bool:
        """Return True if the page has at least one font that is not a known OCR artifact."""
        fonts = page.get_fonts()  # list of (xref, ext, type, basefont, name, encoding, referencer)
        if not fonts:
            return False
        for font_tuple in fonts:
            basefont = font_tuple[3] or ""
            name = font_tuple[4] or ""
            # Try to get font size via text dict
            font_name = basefont or name
            if font_name in _FAKE_FONTS:
                continue
            # Check if any span using this font has size > 0
            blocks = page.get_text("dict").get("blocks", [])
            for block in blocks:
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        span_font = span.get("font", "")
                        span_size = span.get("size", 0)
                        if span_font not in _FAKE_FONTS and span_size > 0:
                            return True
        return False
    ```

    Then create `backend/tests/__init__.py` (empty) and `backend/tests/extraction/__init__.py` (empty) if they do not exist.

    Create `backend/tests/extraction/test_classifier.py` using `unittest.mock` to mock a `fitz.Page` object (do NOT require a real PDF file in unit tests):

    ```python
    """Unit tests for services.extraction.classifier.is_native_page."""
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

    from unittest.mock import MagicMock, patch
    import pytest
    from services.extraction.classifier import is_native_page


    def _make_page(text="", image_area_fraction=0.0, fonts=None, spans=None):
        """Helper: build a mock fitz.Page with controllable signals."""
        page = MagicMock()
        page_width, page_height = 595.0, 842.0  # A4 in points
        page.rect.width = page_width
        page.rect.height = page_height

        page.get_text.return_value = text

        image_area = image_area_fraction * page_width * page_height
        page.get_image_info.return_value = (
            [{"width": image_area ** 0.5, "height": image_area ** 0.5}] if image_area > 0 else []
        )

        # fonts list: (xref, ext, type, basefont, name, encoding, referencer)
        if fonts is None:
            fonts = [("xref1", "Type1", "Type1", "Helvetica", "Helvetica", "WinAnsiEncoding", 0)]
        page.get_fonts.return_value = fonts

        # Build text dict with spans
        if spans is None:
            spans = [{"font": "Helvetica", "size": 12, "text": text}]
        page.get_text.side_effect = lambda mode: (
            text if mode == "text" else {"blocks": [{"lines": [{"spans": spans}]}]}
        )
        return page


    def test_native_page_all_signals_pass():
        page = _make_page(
            text="A" * 100,
            image_area_fraction=0.10,
            fonts=[("x", "T1", "T1", "Helvetica", "Helvetica", "Win", 0)],
            spans=[{"font": "Helvetica", "size": 12, "text": "A" * 100}],
        )
        result = is_native_page(page)
        assert result["is_native"] is True
        assert result["char_count"] == 100
        assert result["has_real_fonts"] is True


    def test_too_few_chars():
        page = _make_page(
            text="A" * 30,
            image_area_fraction=0.05,
            spans=[{"font": "Helvetica", "size": 12, "text": "A" * 30}],
        )
        result = is_native_page(page)
        assert result["is_native"] is False
        assert result["char_count"] == 30


    def test_image_dominant():
        page = _make_page(
            text="A" * 200,
            image_area_fraction=0.70,
            spans=[{"font": "Helvetica", "size": 12, "text": "A" * 200}],
        )
        result = is_native_page(page)
        assert result["is_native"] is False
        assert result["image_coverage"] > 0.60


    def test_glyphlessfont_only():
        page = _make_page(
            text="A" * 200,
            image_area_fraction=0.05,
            fonts=[("x", "T1", "T1", "GlyphLessFont", "GlyphLessFont", "", 0)],
            spans=[{"font": "GlyphLessFont", "size": 12, "text": "A" * 200}],
        )
        result = is_native_page(page)
        assert result["is_native"] is False
        assert result["has_real_fonts"] is False


    def test_size_zero_font():
        page = _make_page(
            text="A" * 200,
            image_area_fraction=0.05,
            fonts=[("x", "T1", "T1", "SomeFont", "SomeFont", "", 0)],
            spans=[{"font": "SomeFont", "size": 0, "text": "A" * 200}],
        )
        result = is_native_page(page)
        assert result["is_native"] is False
        assert result["has_real_fonts"] is False


    def test_mixed_fonts_has_at_least_one_real():
        page = _make_page(
            text="A" * 200,
            image_area_fraction=0.05,
            fonts=[
                ("x1", "T1", "T1", "GlyphLessFont", "GlyphLessFont", "", 0),
                ("x2", "T1", "T1", "Arial", "Arial", "Win", 0),
            ],
            spans=[
                {"font": "GlyphLessFont", "size": 10, "text": "X"},
                {"font": "Arial", "size": 11, "text": "A" * 200},
            ],
        )
        result = is_native_page(page)
        assert result["has_real_fonts"] is True
        assert result["is_native"] is True


    def test_return_dict_has_required_keys():
        page = _make_page(text="Hello world " * 10)
        result = is_native_page(page)
        assert set(result.keys()) == {"is_native", "char_count", "image_coverage", "has_real_fonts"}
    ```
  </action>
  <verify>
    <automated>cd backend && python -m pytest tests/extraction/test_classifier.py -v 2>&1</automated>
  </verify>
  <done>All 7 tests pass (PASSED). No test is FAILED or ERROR. classifier.py exports `is_native_page`.</done>
</task>

</tasks>

<verification>
- `backend/requirements.txt` contains the line `pymupdf==1.24.5`
- `backend/services/extraction/__init__.py` exists
- `backend/services/extraction/classifier.py` contains `def is_native_page(`
- `cd backend && python -m pytest tests/extraction/test_classifier.py -v` exits 0 with 7 passed
- `cd backend && python -c "from services.extraction.classifier import is_native_page; print('ok')"` prints "ok"
</verification>

<success_criteria>
- pymupdf is installed and importable as `fitz`
- `is_native_page(page)` returns a dict with `is_native`, `char_count`, `image_coverage`, `has_real_fonts`
- Classification rules exactly match research spec: char ≥ 50, image < 60%, has real non-GlyphLessFont non-size-0 font
- All unit tests pass without requiring a real PDF file
</success_criteria>

<output>
After completion, create `.planning/phases/01-adaptive-text-extraction/01-1-SUMMARY.md`
</output>
