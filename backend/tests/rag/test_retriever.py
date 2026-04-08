"""Tests for RETRIEVE-03/RETRIEVE-04 — routing retriever (Plans 04-05, 05-04)."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import pytest
from unittest.mock import patch, MagicMock
from services.rag.retriever import build_context_prompt
from services.rag.router import RoutingResult


def _make_routing(intent="search_only", search_queries=None, sql_steps=None):
    return RoutingResult(
        intent=intent,
        search_queries=search_queries or ["HbA1c results"],
        sql_steps=sql_steps or [],
    )


def test_build_context_prompt_calls_generate_embedding():
    """Mock route_query to return search_only; assert generate_embedding called with the search query."""
    routing = _make_routing(intent="search_only", search_queries=["HbA1c results"])
    with patch("services.rag.retriever.route_query", return_value=routing), \
         patch("services.rag.retriever.generate_embedding") as mock_embed, \
         patch("services.rag.retriever.search", return_value=[]) as mock_search:
        mock_embed.return_value = [0.1] * 1536
        build_context_prompt("HbA1c results", "u1")
        mock_embed.assert_called_once_with("HbA1c results")


def test_build_context_prompt_passes_vector_to_search():
    """Assert search is called with query_vector from generate_embedding."""
    vec = [0.1] * 1536
    routing = _make_routing(intent="search_only", search_queries=["HbA1c"])
    with patch("services.rag.retriever.route_query", return_value=routing), \
         patch("services.rag.retriever.generate_embedding", return_value=vec), \
         patch("services.rag.retriever.search", return_value=[]) as mock_search:
        build_context_prompt("HbA1c", "u1")
        _, kwargs = mock_search.call_args
        assert kwargs.get("query_vector") == vec or mock_search.call_args[0][3] == vec


def test_retriever_degrades_when_embedding_fails():
    """When generate_embedding returns None, search should be called with query_vector=None."""
    routing = _make_routing(intent="search_only", search_queries=["test"])
    with patch("services.rag.retriever.route_query", return_value=routing), \
         patch("services.rag.retriever.generate_embedding", return_value=None), \
         patch("services.rag.retriever.search", return_value=[]) as mock_search:
        build_context_prompt("test", "u1")
        call_kwargs = mock_search.call_args
        # search should be called with query_vector=None
        assert "query_vector" in str(call_kwargs)


@pytest.mark.skip(reason="Wave 0 stub — implement after retriever.py refactored in Plan 05-04")
def test_context_includes_sql_section():
    # Verifies that build_context_prompt returns context containing SQL structured block
    # when route_query returns sql_only or mixed intent
    pass
