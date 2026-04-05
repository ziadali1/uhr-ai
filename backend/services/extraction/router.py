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

from services.extraction.classifier import is_native_page
from services.extraction.extractor import extract_text_native, compute_quality_score


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
