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
