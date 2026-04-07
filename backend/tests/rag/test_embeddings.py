"""Tests for services.azure.embeddings — Azure OpenAI embedding generation."""
from unittest.mock import MagicMock, patch

import pytest

from services.azure.embeddings import generate_embedding


def test_generate_embedding_returns_list_of_floats():
    """When mock mode is off and client returns an embedding, result is list[float] of length 1536."""
    mock_embedding = [0.1] * 1536
    mock_response = MagicMock()
    mock_response.data = [MagicMock(embedding=mock_embedding)]

    mock_client = MagicMock()
    mock_client.embeddings.create.return_value = mock_response

    with patch("services.azure.embeddings._use_mock", return_value=False), \
         patch("services.azure.embeddings._get_embedding_client", return_value=mock_client), \
         patch.dict("os.environ", {"AZURE_OPENAI_EMBEDDING_DEPLOYMENT": "text-embedding-3-small"}):
        result = generate_embedding("some text")

    assert result == [0.1] * 1536
    assert len(result) == 1536


def test_generate_embedding_returns_none_on_failure():
    """When client raises an exception, generate_embedding returns None without raising."""
    with patch("services.azure.embeddings._use_mock", return_value=False), \
         patch("services.azure.embeddings._get_embedding_client", side_effect=Exception("network error")), \
         patch.dict("os.environ", {"AZURE_OPENAI_EMBEDDING_DEPLOYMENT": "text-embedding-3-small"}):
        result = generate_embedding("some text")

    assert result is None


def test_generate_embedding_skips_in_mock_mode():
    """When USE_MOCK_AZURE=true, generate_embedding returns None without calling the client."""
    with patch("services.azure.embeddings._use_mock", return_value=True) as mock_use_mock, \
         patch("services.azure.embeddings._get_embedding_client") as mock_client_factory:
        result = generate_embedding("some text")

    assert result is None
    mock_client_factory.assert_not_called()
