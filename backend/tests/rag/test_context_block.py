"""Wave 0 test stubs for RETRIEVE-02 — context block assembly.

These stubs will fail (skip) until Plan 04-03 implements the context block builder.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import pytest


@pytest.mark.skip(reason="Wave 0 stub — implementation in Plan 03")
def test_structured_lab_block_includes_findings():
    """Given a StructuredResult with document_family=structured_lab and a lab finding,
    assert the output contains 'Hemoglobina: 12.5 g/dL [normal]'."""
    from services.rag.context_block import build_context_block
    from models.document import StructuredResult

    sr = StructuredResult(
        document_family="structured_lab",
        structured_data={
            "findings": [
                {"name": "Hemoglobina", "value": "12.5", "unit": "g/dL", "flag": "normal"}
            ]
        },
    )
    result = build_context_block(sr=sr, anonymized_text="fallback text")
    assert "Hemoglobina: 12.5 g/dL [normal]" in result


@pytest.mark.skip(reason="Wave 0 stub — implementation in Plan 03")
def test_imaging_block_includes_impression():
    """Given document_family=imaging_narrative with an impression, assert it appears."""
    from services.rag.context_block import build_context_block
    from models.document import StructuredResult

    sr = StructuredResult(
        document_family="imaging_narrative",
        structured_data={"impression": "Normal chest X-ray"},
    )
    result = build_context_block(sr=sr, anonymized_text="fallback text")
    assert "Normal chest X-ray" in result


@pytest.mark.skip(reason="Wave 0 stub — implementation in Plan 03")
def test_clinical_note_includes_diagnoses():
    """Given document_family=clinical_narrative with diagnoses, assert they appear."""
    from services.rag.context_block import build_context_block
    from models.document import StructuredResult

    sr = StructuredResult(
        document_family="clinical_narrative",
        structured_data={"diagnoses": ["Hipertensao"]},
    )
    result = build_context_block(sr=sr, anonymized_text="fallback text")
    assert "Hipertensao" in result


@pytest.mark.skip(reason="Wave 0 stub — implementation in Plan 03")
def test_medication_block_includes_drug_names():
    """Given document_family=medication_document, assert drug name and dose appear."""
    from services.rag.context_block import build_context_block
    from models.document import StructuredResult

    sr = StructuredResult(
        document_family="medication_document",
        structured_data={"medications": [{"name": "Losartana", "dose": "50mg"}]},
    )
    result = build_context_block(sr=sr, anonymized_text="fallback text")
    assert "Losartana 50mg" in result


@pytest.mark.skip(reason="Wave 0 stub — implementation in Plan 03")
def test_null_structured_result_falls_back_to_anonymized_text():
    """Given sr=None and long anonymized_text, assert output equals first 1000 chars."""
    from services.rag.context_block import build_context_block

    anonymized_text = "x" * 2000
    result = build_context_block(sr=None, anonymized_text=anonymized_text)
    assert result == anonymized_text[:1000]


@pytest.mark.skip(reason="Wave 0 stub — implementation in Plan 03")
def test_empty_structured_result_falls_back():
    """Given all fields empty/missing, assert fallback to anonymized_text[:1000]."""
    from services.rag.context_block import build_context_block
    from models.document import StructuredResult

    sr = StructuredResult(
        document_family="unknown",
        structured_data={},
    )
    anonymized_text = "fallback content here"
    result = build_context_block(sr=sr, anonymized_text=anonymized_text)
    assert result == anonymized_text[:1000]


@pytest.mark.skip(reason="Wave 0 stub — implementation in Plan 03")
def test_block_truncated_at_2000_chars():
    """Given very long content, assert len(result) <= 2000."""
    from services.rag.context_block import build_context_block
    from models.document import StructuredResult

    # Build a structured result with many findings to force long output
    findings = [{"name": f"Test{i}", "value": str(i), "unit": "mg/dL", "flag": "normal"} for i in range(200)]
    sr = StructuredResult(
        document_family="structured_lab",
        structured_data={"findings": findings},
    )
    result = build_context_block(sr=sr, anonymized_text="fallback")
    assert len(result) <= 2000
