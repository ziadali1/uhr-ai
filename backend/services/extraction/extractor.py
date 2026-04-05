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
