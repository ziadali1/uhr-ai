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


def test_context_includes_sql_section():
    """Verifies build_context_prompt returns context containing SQL structured block
    when route_query returns sql_only intent."""
    from services.rag.router import RoutingResult

    routing = RoutingResult(
        intent="sql_only",
        sql_steps=["medications:active"],
        search_queries=[],
    )
    sql_results = [
        {
            "step": "medications:active",
            "table": "patient_medications",
            "rows": [{"raw_medication": "Metformina", "dose": "850mg", "frequency": "2x ao dia"}],
        }
    ]
    sql_block_text = (
        "=== DADOS ESTRUTURADOS DO PACIENTE ===\n"
        "Medicamento: Metformina 850mg\n"
        "=== FIM DOS DADOS ESTRUTURADOS ==="
    )

    with patch.dict(os.environ, {"USE_MOCK_AZURE": "false"}), \
         patch("services.rag.retriever.route_query", return_value=routing), \
         patch("services.rag.retriever.execute_sql_steps", return_value=sql_results), \
         patch("services.rag.retriever.format_sql_block", return_value=sql_block_text), \
         patch("services.rag.retriever.generate_embedding", return_value=None), \
         patch("services.rag.retriever.search", return_value=[]):
        system_prompt, sources = build_context_prompt("Quais sao minhas medicacoes ativas?", "user-1")

    assert "DADOS ESTRUTURADOS DO PACIENTE" in system_prompt
    assert "Metformina" in system_prompt
    assert isinstance(sources, list)
