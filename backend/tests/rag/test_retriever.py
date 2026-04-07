"""Wave 0 test stubs for RETRIEVE-03 — hybrid query retriever.

These stubs will fail (skip) until Plan 04-05 upgrades the retriever.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import pytest


@pytest.mark.skip(reason="Wave 0 stub — implementation in Plan 05")
def test_build_context_prompt_calls_generate_embedding():
    """Mock generate_embedding and search; assert embedding called with the query text."""
    from unittest.mock import patch
    from services.rag.retriever import build_context_prompt

    with patch("services.rag.retriever.generate_embedding") as mock_embed, \
         patch("services.rag.retriever.search", return_value=[]) as mock_search:
        mock_embed.return_value = [0.1] * 1536

        build_context_prompt("What are my lab results?", "user-001")

    mock_embed.assert_called_once_with("What are my lab results?")


@pytest.mark.skip(reason="Wave 0 stub — implementation in Plan 05")
def test_hybrid_search_passes_vectorized_query():
    """Mock the search client; assert vector_queries parameter is passed."""
    from unittest.mock import patch, MagicMock
    from services.azure.search import search

    embedding = [0.1] * 1536

    with patch("services.azure.search._use_mock", return_value=False), \
         patch("services.azure.search.SearchClient") as MockClient:
        mock_client_instance = MagicMock()
        MockClient.return_value = mock_client_instance
        mock_client_instance.search.return_value = []

        search(query="hemoglobina", user_id="user-001", top_k=3, query_vector=embedding)

    call_kwargs = mock_client_instance.search.call_args
    assert call_kwargs is not None
    _, kwargs = call_kwargs
    assert "vector_queries" in kwargs, "vector_queries must be passed to search client"


@pytest.mark.skip(reason="Wave 0 stub — implementation in Plan 05")
def test_retriever_works_in_mock_mode():
    """With USE_MOCK_AZURE=true, call build_context_prompt — assert no embedding call
    and mock search used."""
    from unittest.mock import patch
    import os
    from services.rag.retriever import build_context_prompt

    with patch.dict(os.environ, {"USE_MOCK_AZURE": "true"}), \
         patch("services.rag.retriever.generate_embedding") as mock_embed:

        result_prompt, sources = build_context_prompt("test query", "user-001")

    mock_embed.assert_not_called()
    assert isinstance(result_prompt, str)
    assert isinstance(sources, list)
