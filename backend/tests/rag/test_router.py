"""Tests for RETRIEVE-04 and RETRIEVE-05 — query routing and context assembly (Phase 5)."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import pytest
from unittest.mock import patch, MagicMock
from services.rag.router import (
    expand_abbreviations,
    route_query,
    RoutingResult,
    execute_sql_steps,
    format_sql_block,
    assemble_chat_block,
)


def test_expand_abbreviations():
    result = expand_abbreviations("HbA1c e PA estao altos")
    assert "hemoglobina glicada" in result
    assert "pressão arterial" in result
    assert "HbA1c" not in result
    # non-abbreviation text should be unchanged
    assert expand_abbreviations("normal text") == "normal text"


def test_route_mock_mode():
    with patch.dict(os.environ, {"USE_MOCK_AZURE": "true"}), \
         patch("services.rag.router._use_mock_cache", None), \
         patch("services.rag.router.generate_json") as mock_gen:
        result = route_query("Qual meu HbA1c?", "user-1")
        assert result.intent == "search_only"
        assert isinstance(result, RoutingResult)
        assert mock_gen.call_count == 0


def test_route_narrative_returns_search_only():
    llm_response = '{"intent": "search_only", "entities": ["cardiologista"], "time_range": null, "sql_steps": [], "search_queries": ["o que meu cardiologista disse"]}'
    with patch.dict(os.environ, {"USE_MOCK_AZURE": "false"}), \
         patch("services.rag.router._use_mock_cache", False), \
         patch("services.rag.router.generate_json", return_value=llm_response):
        result = route_query("O que meu cardiologista disse?", "user-1")
        assert result.intent == "search_only"
        assert "cardiologista" in result.entities


def test_route_aggregation_returns_sql_only():
    llm_response = '{"intent": "sql_only", "entities": ["hemoglobina glicada"], "time_range": ["2024-01-01", "2024-12-31"], "sql_steps": ["observations:hemoglobina glicada:range:2024-01-01:2024-12-31"], "search_queries": []}'
    with patch.dict(os.environ, {"USE_MOCK_AZURE": "false"}), \
         patch("services.rag.router._use_mock_cache", False), \
         patch("services.rag.router.generate_json", return_value=llm_response):
        result = route_query("Qual meu HbA1c medio no ano passado?", "user-1")
        assert result.intent == "sql_only"
        assert len(result.sql_steps) > 0
        assert "hemoglobina glicada" in result.sql_steps[0]


def test_route_mixed_intent():
    llm_response = '{"intent": "mixed", "entities": ["medicamentos"], "time_range": null, "sql_steps": ["medications:active"], "search_queries": ["o que meu cardiologista disse sobre medicamentos"]}'
    with patch.dict(os.environ, {"USE_MOCK_AZURE": "false"}), \
         patch("services.rag.router._use_mock_cache", False), \
         patch("services.rag.router.generate_json", return_value=llm_response):
        result = route_query("Minhas medicacoes e o que meu cardiologista disse?", "user-1")
        assert result.intent == "mixed"
        assert "medications:active" in result.sql_steps
        assert len(result.search_queries) > 0


def test_route_fallback_on_llm_failure():
    with patch.dict(os.environ, {"USE_MOCK_AZURE": "false"}), \
         patch("services.rag.router._use_mock_cache", False), \
         patch("services.rag.router.generate_json", side_effect=Exception("LLM error")):
        result = route_query("Qualquer pergunta", "user-1")
        assert result.intent == "search_only"
        assert isinstance(result, RoutingResult)


def test_route_returns_routing_result_model():
    with patch.dict(os.environ, {"USE_MOCK_AZURE": "true"}), \
         patch("services.rag.router._use_mock_cache", None):
        result = route_query("test", "u1")
        assert isinstance(result, RoutingResult)
        assert hasattr(result, "intent")
        assert hasattr(result, "sql_steps")
        assert hasattr(result, "search_queries")


def test_sql_observations_scoped_by_user_id():
    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.data = [
        {
            "normalized_analyte": "hemoglobina glicada",
            "value_str": "7.8",
            "unit": "%",
            "flag": "high",
            "observed_date": "2024-01-15",
        }
    ]
    (
        mock_client.table.return_value
        .select.return_value
        .eq.return_value
        .eq.return_value
        .order.return_value
        .limit.return_value
        .execute.return_value
    ) = mock_resp

    with patch("services.rag.router._get_client", return_value=mock_client):
        results = execute_sql_steps(["observations:hemoglobina glicada"], "user-123")

    assert len(results) == 1
    assert results[0]["table"] == "patient_observations"
    assert len(results[0]["rows"]) == 1


def test_sql_user_isolation():
    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.data = []

    # Build mock chain for medications:active path:
    # .table().select().eq("user_id",...).eq("status","active").limit().execute()
    select_mock = mock_client.table.return_value.select.return_value
    first_eq = select_mock.eq.return_value
    (
        first_eq
        .eq.return_value
        .limit.return_value
        .execute.return_value
    ) = mock_resp

    with patch("services.rag.router._get_client", return_value=mock_client):
        execute_sql_steps(["medications:active"], "user-A")

    # Verify that the first .eq() call on the select chain used "user_id" and "user-A"
    # select_mock.eq is the first .eq() in the chain
    eq_calls = select_mock.eq.call_args_list
    assert any(
        call_args[0][0] == "user_id" and call_args[0][1] == "user-A"
        for call_args in eq_calls
    ), f"Expected eq('user_id', 'user-A') but got: {eq_calls}"


def test_chat_block_structured_lab():
    from models.document import StructuredResult

    sr = StructuredResult(
        document_family="structured_lab",
        structured_data={
            "summary": "Controle glicemico subotimo",
            "findings": [
                {"name": "HbA1c", "value": "7.8", "unit": "%", "flag": "high"}
            ],
            "entities_for_memory": ["diabetes mellitus"],
            "collection_date": "2024-01-15",
        },
    )

    with patch("services.rag.router._fetch_structured_result", return_value=sr):
        result = assemble_chat_block("doc-1", "Hemograma", "raw excerpt", "2024-01-15")

    assert "[Fonte: Hemograma" in result
    assert "HbA1c" in result
    assert "7.8" in result
    assert "[high]" in result
    assert "Summary:" in result


def test_chat_block_fallback():
    with patch("services.rag.router._fetch_structured_result", return_value=None):
        result = assemble_chat_block("doc-1", "Lab Test", "this is the raw excerpt", "2024-01-15")

    assert "[Fonte: Lab Test" in result
    assert "this is the raw excerpt" in result
    assert len(result) <= 1200
