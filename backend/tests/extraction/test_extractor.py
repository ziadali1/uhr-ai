"""Unit tests for services.extraction.extractor."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from unittest.mock import MagicMock, patch
import pytest
from services.extraction.extractor import compute_quality_score, extract_text_native


# ── compute_quality_score tests ───────────────────────────────────────────────

GOOD_MEDICAL_TEXT = """\
Paciente apresenta hemoglobina glicada HbA1c de 7.2%, acima do valor de referência 4.0-5.7%.
Glicemia em jejum: 126 mg/dL. Colesterol total: 198 mg/dL. LDL: 120 mg/dL.
Triglicérides: 145 mg/dL. Creatinina: 0.9 mg/dL. Ureia: 32 mg/dL.
Diagnóstico: Diabetes mellitus tipo 2 controlado. Manter metformina 850mg.
Retorno em 3 meses para novo controle laboratorial. Dr. Carlos Mendes CRM 54321.
""" * 3


def test_score_empty_string():
    assert compute_quality_score("") == 0.0


def test_score_empty_whitespace():
    assert compute_quality_score("   \n\t  ") == 0.0


def test_score_good_medical_text_above_threshold():
    score = compute_quality_score(GOOD_MEDICAL_TEXT)
    assert score >= 0.65, f"Expected >= 0.65, got {score}"


def test_score_non_printable_chars():
    garbage = "\x00\x01\x02\x03\x04\x05" * 50
    score = compute_quality_score(garbage)
    assert score < 0.10, f"Expected < 0.10 for garbage, got {score}"


def test_score_always_in_range():
    for text in ["", "abc", GOOD_MEDICAL_TEXT, "\xff" * 100, "123 456 789"]:
        score = compute_quality_score(text)
        assert 0.0 <= score <= 1.0, f"Score {score} out of [0, 1] for input {repr(text[:30])}"


def test_score_perfect_text_near_one():
    # Construct text with ~15% numeric density, real words, avg line ~60 chars
    line = "Hemoglobina glicada 7.2 mg dL colesterol triglicerides 145 creatinina 0.9"
    perfect = (line + "\n") * 20
    score = compute_quality_score(perfect)
    assert score >= 0.85, f"Expected >= 0.85 for perfect text, got {score}"


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
