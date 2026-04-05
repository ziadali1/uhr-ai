"""Tests for ExtractionMeta model and DocumentDetail integration."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from datetime import datetime, timezone
import pytest
from models.document import ExtractionMeta, DocumentDetail, ExtractedEntity


def _make_meta(**overrides):
    defaults = {
        "method": "native",
        "quality_score": 0.82,
        "page_strategies": [{"is_native": True, "char_count": 200}],
        "library": "pymupdf/1.24.5",
        "fallback_reason": None,
        "extracted_at": datetime.now(timezone.utc).isoformat(),
    }
    defaults.update(overrides)
    return ExtractionMeta(**defaults)


def test_extraction_meta_construction():
    meta = _make_meta()
    assert meta.method == "native"
    assert 0.0 <= meta.quality_score <= 1.0
    assert meta.fallback_reason is None


def test_extraction_meta_ocr_fallback():
    meta = _make_meta(method="ocr", fallback_reason="low_quality", quality_score=0.40)
    assert meta.method == "ocr"
    assert meta.fallback_reason == "low_quality"


def test_extraction_meta_model_dump_is_serializable():
    import json
    meta = _make_meta()
    dumped = meta.model_dump()
    # Must not raise
    serialized = json.dumps(dumped)
    assert "native" in serialized


def test_document_detail_without_meta_is_valid():
    detail = DocumentDetail(
        document_id="doc-1",
        user_id="user-1",
        original_name="test.pdf",
        upload_date=datetime.now(timezone.utc),
        anonymized_text="Some text",
        medical_entities=[],
        pii_substitutions=[],
    )
    assert detail.text_extraction_meta is None


def test_document_detail_with_meta_is_valid():
    meta = _make_meta()
    detail = DocumentDetail(
        document_id="doc-1",
        user_id="user-1",
        original_name="test.pdf",
        upload_date=datetime.now(timezone.utc),
        anonymized_text="Some text",
        medical_entities=[],
        pii_substitutions=[],
        text_extraction_meta=meta,
    )
    assert detail.text_extraction_meta is not None
    assert detail.text_extraction_meta.method == "native"


def test_extraction_meta_from_router_output():
    """Simulate constructing ExtractionMeta from extract_text_with_meta() dict."""
    router_output = {
        "text": "Texto extraído",
        "method": "native",
        "quality_score": 0.88,
        "fallback_reason": None,
        "page_strategies": [{"is_native": True}],
        "library": "pymupdf/1.24.5",
    }
    meta = ExtractionMeta(
        method=router_output["method"],
        quality_score=router_output["quality_score"],
        page_strategies=router_output["page_strategies"],
        library=router_output["library"],
        fallback_reason=router_output["fallback_reason"],
        extracted_at=datetime.now(timezone.utc).isoformat(),
    )
    assert meta.method == "native"
    assert meta.quality_score == 0.88
