---
phase: 01-adaptive-text-extraction
plan: 3
type: execute
wave: 3
depends_on:
  - 01-PLAN-1-page-classifier
  - 01-PLAN-2-native-extraction-quality-score
files_modified:
  - backend/services/extraction/router.py
  - backend/services/azure/document_intelligence.py
  - backend/services/pipeline/orchestrator.py
  - backend/tests/extraction/test_router.py
autonomous: true
requirements:
  - INGEST-02
  - INGEST-03

must_haves:
  truths:
    - "Calling extract_text(file_bytes, filename) on a native-text PDF returns text WITHOUT calling Azure Document Intelligence"
    - "Calling extract_text(file_bytes, filename) on a non-PDF file routes directly to OCR"
    - "Calling extract_text(file_bytes, filename) on a scanned PDF routes to OCR"
    - "The function signature extract_text(file_bytes: bytes, filename: str) -> str is unchanged"
    - "orchestrator.py requires zero changes — it imports from the same path and calls the same function"
    - "The routing decision (native vs OCR) is determined by is_native_page() across all pages, with the logic: all-native AND score>=0.65 → native; otherwise → OCR"
  artifacts:
    - path: "backend/services/extraction/router.py"
      provides: "extract_text_adaptive() — the core routing function"
      exports: ["extract_text_adaptive"]
    - path: "backend/services/azure/document_intelligence.py"
      provides: "extract_text() now delegates to adaptive router"
      contains: "extract_text_adaptive"
    - path: "backend/tests/extraction/test_router.py"
      provides: "Pytest tests for routing logic"
  key_links:
    - from: "backend/services/azure/document_intelligence.py"
      to: "backend/services/extraction/router.py"
      via: "from services.extraction.router import extract_text_adaptive"
      pattern: "from services.extraction.router import extract_text_adaptive"
    - from: "backend/services/extraction/router.py"
      to: "backend/services/extraction/extractor.py"
      via: "from services.extraction.extractor import extract_text_native, compute_quality_score"
      pattern: "from services.extraction.extractor import"
    - from: "backend/services/pipeline/orchestrator.py"
      to: "backend/services/azure/document_intelligence.py"
      via: "from services.azure.document_intelligence import extract_text"
      pattern: "from services.azure.document_intelligence import extract_text"
---

<objective>
Wire the classifier, extractor, and quality scorer into a routing function, then update `document_intelligence.py` to use it — keeping the `extract_text(file_bytes, filename) -> str` interface that the orchestrator already calls.

Purpose: This is the integration plan. The orchestrator must not change. The document_intelligence module becomes a thin shim that delegates to the adaptive router. No caller notices the difference; the behavior changes internally.
Output: `services/extraction/router.py` with `extract_text_adaptive()`; updated `document_intelligence.py`; zero changes to `orchestrator.py`.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/research/extraction.md
@backend/services/azure/document_intelligence.py
@backend/services/pipeline/orchestrator.py
@backend/services/extraction/classifier.py
@backend/services/extraction/extractor.py
</context>

<interfaces>
<!-- Contracts this plan must preserve and use. -->

Existing interface (orchestrator.py line 18 + line 107 — MUST NOT CHANGE):
```python
from services.azure.document_intelligence import extract_text
# ...
raw_text = extract_text(file_bytes, filename)
```

From Plan 1 — classifier.py:
```python
def is_native_page(page) -> dict:
    # returns: is_native (bool), char_count (int), image_coverage (float), has_real_fonts (bool)
```

From Plan 2 — extractor.py:
```python
def extract_text_native(file_bytes: bytes) -> str: ...
def compute_quality_score(text: str) -> float: ...
```
</interfaces>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Implement extract_text_adaptive() router</name>
  <read_first>
    .planning/research/extraction.md
    backend/services/extraction/classifier.py
    backend/services/extraction/extractor.py
  </read_first>
  <files>
    backend/services/extraction/router.py
    backend/tests/extraction/test_router.py
  </files>
  <behavior>
    Routing rules (from research spec, exactly):
    - If filename does NOT end in ".pdf" (case-insensitive) → route to OCR, method="ocr"
    - If PDF and ALL pages are native AND quality score >= 0.65 → use native, method="native"
    - If PDF and ALL pages are native BUT quality score < 0.65 → fallback to OCR, method="ocr", fallback_reason="low_quality"
    - If PDF and ALL pages are scanned (none native) → OCR, method="ocr"
    - If PDF and MIXED pages (some native, some not) → OCR (v1 safe fallback), method="ocr", fallback_reason="mixed_pages"

    Return value of extract_text_adaptive():
    dict with keys:
      text (str): the extracted text
      method (str): "native" | "ocr"
      quality_score (float): score from compute_quality_score applied to the final text
      fallback_reason (str | None): reason native was rejected, or None
      page_strategies (list[dict]): per-page classification result dicts from is_native_page()
      library (str): "pymupdf/{version}" for native, "azure-ai-formrecognizer/3.3.3" for ocr

    Test cases:
    - Test 1: non-PDF filename → method=="ocr", OCR function called once
    - Test 2: all-native pages, score >= 0.65 → method=="native", OCR function NOT called
    - Test 3: all-native pages, score < 0.65 → method=="ocr", fallback_reason=="low_quality"
    - Test 4: all-scanned pages → method=="ocr"
    - Test 5: mixed pages → method=="ocr", fallback_reason=="mixed_pages"
    - Test 6: return dict has all required keys
  </behavior>
  <action>
    Create `backend/services/extraction/router.py`:

    ```python
    """
    Adaptive text extraction router.

    Routing logic (v1):
      - non-PDF → OCR
      - all-native pages + score >= 0.65 → native
      - all-native pages + score < 0.65  → OCR (low quality)
      - all-scanned pages               → OCR
      - mixed pages                     → OCR (v1 safe fallback; v2 will do page-level routing)

    The function `extract_text_ocr` is passed as a callable argument to allow mocking in tests
    and to avoid a circular import with document_intelligence.py.
    """
    from __future__ import annotations

    import fitz


    _QUALITY_THRESHOLD = 0.65


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
        """
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

        # Classify all pages
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        page_strategies: list[dict] = [is_native_page(page) for page in doc]
        doc.close()

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

    Create `backend/tests/extraction/test_router.py`:

    ```python
    """Unit tests for services.extraction.router.extract_text_adaptive."""
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

    from unittest.mock import MagicMock, patch
    import pytest
    from services.extraction.router import extract_text_adaptive

    REQUIRED_KEYS = {"text", "method", "quality_score", "fallback_reason", "page_strategies", "library"}


    def _mock_ocr(text="OCR result"):
        fn = MagicMock(return_value=text)
        return fn


    def test_non_pdf_routes_to_ocr():
        ocr_fn = _mock_ocr("OCR result from image")
        with patch("services.extraction.router.fitz") as mock_fitz:
            result = extract_text_adaptive(b"fake", "scan.jpg", ocr_fn)
        assert result["method"] == "ocr"
        ocr_fn.assert_called_once()


    def test_all_native_high_score_uses_native():
        ocr_fn = _mock_ocr()
        native_classify = {"is_native": True, "char_count": 200, "image_coverage": 0.05, "has_real_fonts": True}

        with patch("services.extraction.router.fitz") as mock_fitz, \
             patch("services.extraction.router.is_native_page", return_value=native_classify), \
             patch("services.extraction.router.extract_text_native", return_value="Texto nativo longo e rico" * 20), \
             patch("services.extraction.router.compute_quality_score", return_value=0.80):
            mock_page = MagicMock()
            mock_doc = MagicMock()
            mock_doc.__iter__ = MagicMock(return_value=iter([mock_page]))
            mock_doc.close = MagicMock()
            mock_fitz.open.return_value = mock_doc

            result = extract_text_adaptive(b"%PDF fake", "laudo.pdf", ocr_fn)

        assert result["method"] == "native"
        assert result["quality_score"] == 0.80
        ocr_fn.assert_not_called()


    def test_all_native_low_score_falls_back_to_ocr():
        ocr_fn = _mock_ocr("OCR fallback text")
        native_classify = {"is_native": True, "char_count": 200, "image_coverage": 0.05, "has_real_fonts": True}

        with patch("services.extraction.router.fitz") as mock_fitz, \
             patch("services.extraction.router.is_native_page", return_value=native_classify), \
             patch("services.extraction.router.extract_text_native", return_value="garbage"), \
             patch("services.extraction.router.compute_quality_score", side_effect=[0.40, 0.55]):
            mock_page = MagicMock()
            mock_doc = MagicMock()
            mock_doc.__iter__ = MagicMock(return_value=iter([mock_page]))
            mock_doc.close = MagicMock()
            mock_fitz.open.return_value = mock_doc

            result = extract_text_adaptive(b"%PDF fake", "laudo.pdf", ocr_fn)

        assert result["method"] == "ocr"
        assert result["fallback_reason"] == "low_quality"
        ocr_fn.assert_called_once()


    def test_all_scanned_routes_to_ocr():
        ocr_fn = _mock_ocr("OCR from scanned PDF")
        scanned_classify = {"is_native": False, "char_count": 5, "image_coverage": 0.90, "has_real_fonts": False}

        with patch("services.extraction.router.fitz") as mock_fitz, \
             patch("services.extraction.router.is_native_page", return_value=scanned_classify), \
             patch("services.extraction.router.compute_quality_score", return_value=0.70):
            mock_page = MagicMock()
            mock_doc = MagicMock()
            mock_doc.__iter__ = MagicMock(return_value=iter([mock_page]))
            mock_doc.close = MagicMock()
            mock_fitz.open.return_value = mock_doc

            result = extract_text_adaptive(b"%PDF fake", "scan.pdf", ocr_fn)

        assert result["method"] == "ocr"
        ocr_fn.assert_called_once()


    def test_mixed_pages_routes_to_ocr_with_reason():
        ocr_fn = _mock_ocr("OCR mixed")
        page1_classify = {"is_native": True, "char_count": 200, "image_coverage": 0.05, "has_real_fonts": True}
        page2_classify = {"is_native": False, "char_count": 5, "image_coverage": 0.90, "has_real_fonts": False}

        with patch("services.extraction.router.fitz") as mock_fitz, \
             patch("services.extraction.router.is_native_page", side_effect=[page1_classify, page2_classify]), \
             patch("services.extraction.router.compute_quality_score", return_value=0.70):
            mock_doc = MagicMock()
            mock_doc.__iter__ = MagicMock(return_value=iter([MagicMock(), MagicMock()]))
            mock_doc.close = MagicMock()
            mock_fitz.open.return_value = mock_doc

            result = extract_text_adaptive(b"%PDF fake", "mixed.pdf", ocr_fn)

        assert result["method"] == "ocr"
        assert result["fallback_reason"] == "mixed_pages"


    def test_return_dict_has_all_required_keys():
        ocr_fn = _mock_ocr()
        with patch("services.extraction.router.fitz"):
            result = extract_text_adaptive(b"fake", "image.png", ocr_fn)
        assert REQUIRED_KEYS.issubset(set(result.keys()))
    ```
  </action>
  <verify>
    <automated>cd backend && python -m pytest tests/extraction/test_router.py -v 2>&1</automated>
  </verify>
  <done>All 6 router tests pass. `extract_text_adaptive` is importable from `services.extraction.router`.</done>
</task>

<task type="auto">
  <name>Task 2: Update document_intelligence.py to delegate to adaptive router</name>
  <read_first>
    backend/services/azure/document_intelligence.py
    backend/services/pipeline/orchestrator.py
  </read_first>
  <files>
    backend/services/azure/document_intelligence.py
  </files>
  <action>
    Replace the entire contents of `backend/services/azure/document_intelligence.py` with the following.
    The public function signature `extract_text(file_bytes: bytes, filename: str) -> str` is UNCHANGED so orchestrator.py requires zero edits.

    ```python
    """
    Azure Document Intelligence — OCR de PDFs e imagens de laudos médicos.
    Com USE_MOCK_AZURE=true, retorna texto de exemplo sem Azure real.

    v2: extract_text() now delegates to the adaptive router in services/extraction/router.py.
    Native-text PDFs are extracted via PyMuPDF when quality score >= 0.65.
    OCR (Azure Document Intelligence) is used as fallback.

    The public interface is unchanged: extract_text(file_bytes, filename) -> str.
    Callers that need extraction metadata should call extract_text_with_meta() instead.
    """
    import os
    from io import BytesIO


    def _use_mock() -> bool:
        return os.getenv("USE_MOCK_AZURE", "true").lower() == "true"


    _MOCK_TEXT = """
    LAUDO MÉDICO
    Paciente: João Silva
    CPF: 123.456.789-00
    Data de nascimento: 15/03/1965
    CRM médico: 12345-SP

    Diagnóstico: Diabetes mellitus tipo 2 (CID E11)
    Fibrilação atrial paroxística (CID I48)

    Medicamentos em uso:
    - Metformina 850mg - 2x ao dia
    - Warfarina 5mg - 1x ao dia (INR alvo 2,0-3,0)

    Alergias conhecidas:
    - Dipirona (reação anafilática severa)
    - Penicilina (urticária)

    Tipo sanguíneo: A positivo

    Observações: Paciente com risco cirúrgico elevado devido ao uso de anticoagulante.
    Necessário avaliar suspensão da Warfarina 5 dias antes de qualquer procedimento.

    Dr. Maria Souza - CRM 54321-SP
    Data: 15/03/2024
    """


    def _extract_text_ocr(file_bytes: bytes, filename: str) -> str:
        """
        Call Azure Document Intelligence (prebuilt-read) to OCR a document.
        This is the raw OCR implementation used as fallback by the adaptive router.
        """
        if _use_mock():
            return _MOCK_TEXT.strip()

        from azure.ai.formrecognizer import DocumentAnalysisClient
        from azure.core.credentials import AzureKeyCredential

        endpoint = os.environ["DOCUMENT_INTELLIGENCE_ENDPOINT"]
        key = os.environ["DOCUMENT_INTELLIGENCE_KEY"]

        client = DocumentAnalysisClient(endpoint, AzureKeyCredential(key))
        poller = client.begin_analyze_document(
            "prebuilt-read",
            document=BytesIO(file_bytes),
        )
        result = poller.result()

        lines = []
        for page in result.pages:
            for line in (page.lines or []):
                lines.append(line.content)

        return "\n".join(lines)


    def extract_text_with_meta(file_bytes: bytes, filename: str) -> dict:
        """
        Adaptive extraction with full metadata.

        Returns dict with keys:
          text            (str)
          method          (str)   "native" | "ocr"
          quality_score   (float)
          fallback_reason (str | None)
          page_strategies (list[dict])
          library         (str)

        Use this function when you need to persist text_extraction_meta.
        """
        if _use_mock():
            return {
                "text": _MOCK_TEXT.strip(),
                "method": "ocr",
                "quality_score": 0.85,
                "fallback_reason": None,
                "page_strategies": [],
                "library": "mock",
            }

        from services.extraction.router import extract_text_adaptive
        return extract_text_adaptive(file_bytes, filename, _extract_text_ocr)


    def extract_text(file_bytes: bytes, filename: str) -> str:
        """
        Extract text from a PDF or image.

        Drop-in replacement for the original OCR-only implementation.
        Now routes through the adaptive extractor (native PyMuPDF when quality >= 0.65,
        OCR fallback otherwise).

        Returns the extracted text string. For full extraction metadata, use
        extract_text_with_meta() instead.
        """
        return extract_text_with_meta(file_bytes, filename)["text"]
    ```

    After writing the file, verify that `orchestrator.py` still imports without modification:
    - Line 18 in orchestrator.py reads `from services.azure.document_intelligence import extract_text`
    - Line 107 in orchestrator.py reads `raw_text = extract_text(file_bytes, filename)`
    - Neither line requires changes.
  </action>
  <verify>
    <automated>cd backend && python -c "from services.azure.document_intelligence import extract_text, extract_text_with_meta; print('ok')"</automated>
  </verify>
  <done>
    Both `extract_text` and `extract_text_with_meta` are importable.
    `document_intelligence.py` contains `extract_text_adaptive` (grep confirms delegation).
    `orchestrator.py` is NOT modified (git diff shows no changes to orchestrator.py).
  </done>
</task>

</tasks>

<verification>
- `cd backend && python -m pytest tests/extraction/test_router.py -v` exits 0
- `cd backend && python -c "from services.azure.document_intelligence import extract_text; print(extract_text(b'', 'test.jpg'))"` prints mock text
- `cd backend && python -c "from services.pipeline.orchestrator import run; print('ok')"` prints "ok" (import chain works)
- `git diff backend/services/pipeline/orchestrator.py` shows no changes
- `backend/services/azure/document_intelligence.py` contains string `extract_text_adaptive`
</verification>

<success_criteria>
- Routing logic: all-native + score>=0.65 → native; all-native + score<0.65 → OCR with fallback_reason; mixed → OCR; non-PDF → OCR
- `extract_text(file_bytes, filename) -> str` interface unchanged — orchestrator.py works without modification
- `extract_text_with_meta()` available for Plan 4 to use when persisting metadata
- All tests pass
</success_criteria>

<output>
After completion, create `.planning/phases/01-adaptive-text-extraction/01-3-SUMMARY.md`
</output>
