"""Tests for medical PDF edge cases in router.py."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from unittest.mock import MagicMock, patch, PropertyMock
import pytest
from services.extraction.router import (
    extract_text_adaptive,
    PasswordProtectedError,
    _avg_line_length,
    _apply_qr_code_guard,
)


def _mock_ocr_fn(text="OCR result"):
    fn = MagicMock(return_value=text)
    return fn


# ── Password protection ───────────────────────────────────────────────────────

def test_password_protected_raises_error():
    ocr_fn = _mock_ocr_fn()
    with patch("services.extraction.router.fitz") as mock_fitz:
        mock_doc = MagicMock()
        mock_doc.is_encrypted = True
        mock_doc.authenticate.return_value = 0  # authentication failed
        mock_fitz.open.return_value = mock_doc

        with pytest.raises(PasswordProtectedError):
            extract_text_adaptive(b"%PDF fake", "protected.pdf", ocr_fn)

    ocr_fn.assert_not_called()


def test_print_only_protection_proceeds_normally():
    """PDF with print-only password — authenticate('') succeeds."""
    ocr_fn = _mock_ocr_fn()
    native_classify = {"is_native": True, "char_count": 200, "image_coverage": 0.05, "has_real_fonts": True}

    with patch("services.extraction.router.fitz") as mock_fitz, \
         patch("services.extraction.router.is_native_page", return_value=native_classify), \
         patch("services.extraction.router.extract_text_native", return_value="Texto do laudo"), \
         patch("services.extraction.router.compute_quality_score", return_value=0.80):
        mock_page = MagicMock()
        mock_page.get_text.return_value = "Texto do laudo"
        mock_doc = MagicMock()
        mock_doc.is_encrypted = True
        mock_doc.authenticate.return_value = 1  # success
        mock_doc.__iter__ = MagicMock(return_value=iter([mock_page]))
        mock_doc.close = MagicMock()
        mock_fitz.open.return_value = mock_doc
        mock_fitz.__version__ = "1.23.0"

        result = extract_text_adaptive(b"%PDF fake", "print-locked.pdf", ocr_fn)

    assert result["method"] == "native"
    ocr_fn.assert_not_called()


# ── Corrupt PDF ───────────────────────────────────────────────────────────────

def test_corrupt_pdf_falls_back_to_ocr():
    ocr_fn = _mock_ocr_fn("OCR from corrupt PDF")
    with patch("services.extraction.router.fitz") as mock_fitz, \
         patch("services.extraction.router.compute_quality_score", return_value=0.70):
        mock_fitz.open.side_effect = Exception("truncated file")

        result = extract_text_adaptive(b"not a pdf", "corrupt.pdf", ocr_fn)

    assert result["method"] == "ocr"
    assert result["fallback_reason"] == "corrupt_pdf"
    ocr_fn.assert_called_once()


# ── QR code guard ─────────────────────────────────────────────────────────────

def test_avg_line_length_single_long_line():
    text = "https://example.com/qr/" + "x" * 350
    assert _avg_line_length(text) > 300


def test_avg_line_length_normal_text():
    text = "Hemoglobina glicada: 7.2%\nGlicemia: 126 mg/dL\nColesterol: 198 mg/dL"
    assert _avg_line_length(text) < 60


def test_qr_code_guard_reclassifies_long_line_pages():
    strategies = [
        {"is_native": True, "char_count": 380, "image_coverage": 0.05, "has_real_fonts": True},
    ]
    long_url = "https://qr.hospital.com.br/laudo/" + "a" * 340
    page_texts = [long_url]

    result = _apply_qr_code_guard(strategies, page_texts)
    assert result[0]["is_native"] is False
    assert result[0].get("qr_code_guard") is True


def test_qr_code_guard_preserves_normal_pages():
    strategies = [
        {"is_native": True, "char_count": 200, "image_coverage": 0.05, "has_real_fonts": True},
    ]
    normal_text = "Hemoglobina glicada: 7.2%\nGlicemia: 126 mg/dL"
    result = _apply_qr_code_guard(strategies, [normal_text])
    assert result[0]["is_native"] is True
    assert "qr_code_guard" not in result[0]


# ── AcroForm fields ───────────────────────────────────────────────────────────

def test_acroform_widget_values_included_in_native_text():
    """Verify that page.widgets() values are appended by extract_text_native()."""
    from services.extraction.extractor import extract_text_native

    with patch("services.extraction.extractor.fitz") as mock_fitz, \
         patch("services.extraction.extractor.is_native_page") as mock_classify:
        mock_classify.return_value = {
            "is_native": True, "char_count": 100, "image_coverage": 0.05, "has_real_fonts": True
        }
        widget = MagicMock()
        widget.field_value = "Amoxicilina 500mg - 3x ao dia"
        mock_page = MagicMock()
        mock_page.get_text.return_value = "Prescrição eletrônica MEMED"
        mock_page.widgets.return_value = [widget]
        mock_doc = MagicMock()
        mock_doc.__iter__ = MagicMock(return_value=iter([mock_page]))
        mock_doc.close = MagicMock()
        mock_fitz.open.return_value = mock_doc

        text = extract_text_native(b"%PDF fake")

    assert "Amoxicilina 500mg" in text
    assert "Prescrição eletrônica MEMED" in text
