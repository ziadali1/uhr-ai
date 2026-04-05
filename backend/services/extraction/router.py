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

import logging

import fitz
from services.extraction.classifier import is_native_page
from services.extraction.extractor import extract_text_native, compute_quality_score

_logger = logging.getLogger(__name__)

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
        _logger.warning("Corrupt PDF detected, falling back to OCR: %s", exc)
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
