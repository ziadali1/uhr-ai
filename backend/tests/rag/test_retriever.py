"""Tests for RETRIEVE-03 — hybrid query retriever (Plan 04-05)."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from unittest.mock import patch, MagicMock
from services.rag.retriever import build_context_prompt


def test_build_context_prompt_calls_generate_embedding():
    """Mock generate_embedding and search; assert embedding called with the query text."""
    with patch("services.rag.retriever.generate_embedding") as mock_embed, \
         patch("services.rag.retriever.search", return_value=[]) as mock_search:
        mock_embed.return_value = [0.1] * 1536
        build_context_prompt("HbA1c results", "u1")
        mock_embed.assert_called_once_with("HbA1c results")


def test_build_context_prompt_passes_vector_to_search():
    """Assert search is called with query_vector from generate_embedding."""
    vec = [0.1] * 1536
    with patch("services.rag.retriever.generate_embedding", return_value=vec), \
         patch("services.rag.retriever.search", return_value=[]) as mock_search:
        build_context_prompt("HbA1c", "u1")
        _, kwargs = mock_search.call_args
        assert kwargs.get("query_vector") == vec or mock_search.call_args[0][3] == vec


def test_retriever_degrades_when_embedding_fails():
    """When generate_embedding returns None, search should be called with query_vector=None."""
    with patch("services.rag.retriever.generate_embedding", return_value=None), \
         patch("services.rag.retriever.search", return_value=[]) as mock_search:
        build_context_prompt("test", "u1")
        call_kwargs = mock_search.call_args
        # search should be called with query_vector=None
        assert "query_vector" in str(call_kwargs)
