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
        mock_fitz.__version__ = "1.24.0"
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
