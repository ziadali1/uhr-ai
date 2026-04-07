"""Wave 0 test stubs for RETRIEVE-02 — indexer update with vector support.

These stubs will fail (skip) until Plan 04-04 updates index_after_upload().
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import pytest


@pytest.mark.skip(reason="Wave 0 stub — implementation in Plan 04")
def test_index_after_upload_calls_generate_embedding():
    """Mock generate_embedding and index_document; assert generate_embedding was called."""
    from unittest.mock import patch, MagicMock
    from services.rag.indexer import index_after_upload

    with patch("services.rag.indexer.generate_embedding") as mock_embed, \
         patch("services.rag.indexer.index_document") as mock_index:
        mock_embed.return_value = [0.1] * 1536

        index_after_upload(
            doc_id="doc-001",
            user_id="user-001",
            anonymized_text="Patient has hypertension.",
            source_name="test_doc.pdf",
            entities=[],
        )

    mock_embed.assert_called_once()


@pytest.mark.skip(reason="Wave 0 stub — implementation in Plan 04")
def test_index_after_upload_passes_vector_to_index_document():
    """Mock embedding return as [0.1]*1536; assert index_document received content_vector."""
    from unittest.mock import patch, call
    from services.rag.indexer import index_after_upload

    embedding = [0.1] * 1536

    with patch("services.rag.indexer.generate_embedding", return_value=embedding) as mock_embed, \
         patch("services.rag.indexer.index_document") as mock_index:

        index_after_upload(
            doc_id="doc-001",
            user_id="user-001",
            anonymized_text="Patient has hypertension.",
            source_name="test_doc.pdf",
            entities=[],
        )

    call_kwargs = mock_index.call_args
    assert call_kwargs is not None
    # content_vector may be passed as positional or keyword arg
    args, kwargs = call_kwargs
    passed_vector = kwargs.get("content_vector") or (args[5] if len(args) > 5 else None)
    assert passed_vector == embedding


@pytest.mark.skip(reason="Wave 0 stub — implementation in Plan 04")
def test_index_after_upload_works_without_embedding():
    """Mock embedding return as None; assert index_document still called (without vector)."""
    from unittest.mock import patch
    from services.rag.indexer import index_after_upload

    with patch("services.rag.indexer.generate_embedding", return_value=None) as mock_embed, \
         patch("services.rag.indexer.index_document") as mock_index:

        index_after_upload(
            doc_id="doc-002",
            user_id="user-001",
            anonymized_text="Patient data.",
            source_name="test_doc2.pdf",
            entities=[],
        )

    mock_index.assert_called_once()
