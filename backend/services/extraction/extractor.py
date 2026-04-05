"""
Native PDF text extraction and quality scoring.

extract_text_native(): PyMuPDF-based extraction, per-page, with AcroForm support.
compute_quality_score(): 4-signal weighted quality score [0, 1].
"""
from __future__ import annotations

import re
import string
import unicodedata

import fitz  # pymupdf
from services.extraction.classifier import is_native_page


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
    # Only count lines containing at least one printable character to avoid
    # falsely rewarding garbage blobs that happen to have no newlines.
    lines = [
        line for line in text.splitlines()
        if any(c in string.printable or unicodedata.category(c) not in ("Cc", "Cs") for c in line)
    ]
    avg_line_length = sum(len(line) for line in lines) / max(len(lines), 1) if lines else 0.0
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
