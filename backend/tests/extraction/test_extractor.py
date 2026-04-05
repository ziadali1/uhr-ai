"""Unit tests for services.extraction.extractor."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from unittest.mock import MagicMock, patch
import pytest
from services.extraction.extractor import extract_text_native


# ── extract_text_native tests ─────────────────────────────────────────────────

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
