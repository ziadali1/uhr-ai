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
