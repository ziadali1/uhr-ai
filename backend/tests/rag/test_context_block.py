"""Tests for services.rag.context_block — structured context block assembly."""
import pytest

from services.rag.context_block import assemble_context_block
from models.document import StructuredResult


def test_structured_lab_block_includes_findings():
    sr = StructuredResult(
        document_family="structured_lab",
        structured_data={
            "findings": [
                {"name": "Hemoglobina", "value": "12.5", "unit": "g/dL", "flag": "normal"}
            ]
        },
    )
    result = assemble_context_block(sr, "fallback text")
    assert "Hemoglobina: 12.5 g/dL [normal]" in result


def test_imaging_block_includes_impression():
    sr = StructuredResult(
        document_family="imaging_narrative",
        structured_data={"impression": "Normal chest X-ray"},
    )
    result = assemble_context_block(sr, "fallback text")
    assert "Normal chest X-ray" in result


def test_clinical_note_includes_diagnoses():
    sr = StructuredResult(
        document_family="clinical_narrative",
        structured_data={"diagnoses": ["Hipertensao"]},
    )
    result = assemble_context_block(sr, "fallback text")
    assert "Hipertensao" in result


def test_medication_block_includes_drug_names():
    sr = StructuredResult(
        document_family="medication_document",
        structured_data={"medications": [{"name": "Losartana", "dose": "50mg"}]},
    )
    result = assemble_context_block(sr, "fallback text")
    assert "Losartana 50mg" in result


def test_null_structured_result_falls_back_to_anonymized_text():
    anonymized_text = "x" * 2000
    result = assemble_context_block(None, anonymized_text)
    assert result == "x" * 1000


def test_empty_structured_result_falls_back():
    sr = StructuredResult(
        document_family="structured_lab",
        structured_data={},
        entities_for_memory=[],
    )
    anonymized_text = "fallback content"
    result = assemble_context_block(sr, anonymized_text)
    assert result == anonymized_text[:1000]


def test_block_truncated_at_2000_chars():
    # Create a lab with many findings to generate long content
    findings = [
        {"name": f"Test{i}", "value": str(i), "unit": "mg/dL", "flag": "normal"}
        for i in range(200)
    ]
    sr = StructuredResult(
        document_family="structured_lab",
        structured_data={"findings": findings},
    )
    result = assemble_context_block(sr, "fallback text")
    assert len(result) <= 2000
