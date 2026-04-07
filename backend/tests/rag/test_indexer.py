"""Tests for RETRIEVE-02 — indexer update with context block + embedding.

Plan 04-04: index_after_upload assembles context block, generates embedding (soft-fail),
passes vector + metadata to index_document.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import pytest
from unittest.mock import patch, MagicMock, call
from models.document import StructuredResult
from services.rag.indexer import index_after_upload


def _make_structured_result():
    return StructuredResult(
        document_family="structured_lab",
        structured_data={
            "findings": [{"name": "HbA1c", "value": "6.5", "unit": "%", "flag": "normal"}]
        },
    )


def test_index_after_upload_calls_generate_embedding():
    """Mock generate_embedding and index_document; assert generate_embedding was called with assembled context block."""
    sr = _make_structured_result()

    with patch("services.rag.indexer.assemble_context_block", return_value="HbA1c: 6.5 % [normal]") as mock_assemble, \
         patch("services.rag.indexer.generate_embedding", return_value=[0.1] * 1536) as mock_embed, \
         patch("services.rag.indexer.index_document") as mock_index:

        index_after_upload(
            doc_id="d1",
            user_id="u1",
            anonymized_text="raw text",
            source_name="test.pdf",
            entities=[],
            structured_result=sr,
        )

    mock_assemble.assert_called_once_with(sr, "raw text")
    mock_embed.assert_called_once_with("HbA1c: 6.5 % [normal]")


def test_index_after_upload_passes_vector_to_index_document():
    """Mock embedding return as [0.1]*1536; assert index_document received content_vector=[0.1]*1536."""
    sr = _make_structured_result()
    embedding = [0.1] * 1536

    with patch("services.rag.indexer.assemble_context_block", return_value="context block text"), \
         patch("services.rag.indexer.generate_embedding", return_value=embedding), \
         patch("services.rag.indexer.index_document") as mock_index:

        index_after_upload(
            doc_id="d1",
            user_id="u1",
            anonymized_text="raw text",
            source_name="test.pdf",
            entities=[],
            structured_result=sr,
        )

    call_kwargs = mock_index.call_args
    assert call_kwargs is not None
    _, kwargs = call_kwargs
    assert kwargs.get("content_vector") == embedding


def test_index_after_upload_works_without_embedding():
    """Mock embedding return as None; assert index_document was still called (content_vector=None)."""
    sr = _make_structured_result()

    with patch("services.rag.indexer.assemble_context_block", return_value="context block text"), \
         patch("services.rag.indexer.generate_embedding", return_value=None), \
         patch("services.rag.indexer.index_document") as mock_index:

        index_after_upload(
            doc_id="d2",
            user_id="u1",
            anonymized_text="Patient data.",
            source_name="test_doc2.pdf",
            entities=[],
            structured_result=sr,
        )

    mock_index.assert_called_once()
    _, kwargs = mock_index.call_args
    assert kwargs.get("content_vector") is None
