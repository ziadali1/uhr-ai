"""Wave 0 test stubs for RETRIEVE-02 — embedding generation.

These stubs will fail (skip) until Plan 04-03 implements generate_embedding().
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import pytest


@pytest.mark.skip(reason="Wave 0 stub — implementation in Plan 03")
def test_generate_embedding_returns_list_of_floats():
    """Mock the OpenAI client; assert return is list[float] of length 1536."""
    from unittest.mock import patch, MagicMock
    from services.rag.embeddings import generate_embedding

    mock_response = MagicMock()
    mock_response.data = [MagicMock(embedding=[0.1] * 1536)]

    with patch("services.rag.embeddings._get_client") as mock_client_fn:
        mock_client = MagicMock()
        mock_client.embeddings.create.return_value = mock_response
        mock_client_fn.return_value = mock_client

        result = generate_embedding("test query")

    assert isinstance(result, list)
    assert len(result) == 1536
    assert all(isinstance(v, float) for v in result)


@pytest.mark.skip(reason="Wave 0 stub — implementation in Plan 03")
def test_generate_embedding_returns_none_on_failure():
    """Mock the client to raise Exception; assert return is None."""
    from unittest.mock import patch
    from services.rag.embeddings import generate_embedding

    with patch("services.rag.embeddings._get_client") as mock_client_fn:
        mock_client_fn.side_effect = Exception("Azure connection error")
        result = generate_embedding("test query")

    assert result is None


@pytest.mark.skip(reason="Wave 0 stub — implementation in Plan 03")
def test_generate_embedding_skips_in_mock_mode():
    """Patch _use_mock to return True; assert returns None without calling OpenAI."""
    from unittest.mock import patch, MagicMock
    from services.rag.embeddings import generate_embedding

    with patch("services.rag.embeddings._use_mock", return_value=True) as mock_mode, \
         patch("services.rag.embeddings._get_client") as mock_client_fn:
        result = generate_embedding("test query")

    assert result is None
    mock_client_fn.assert_not_called()
