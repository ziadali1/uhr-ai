"""Wave 0 stubs for patient_query service layer.

All tests are skipped (Wave 0) — will be unskipped in Task 2 once
patient_query.py is implemented.
"""
import pytest


@pytest.mark.skip(reason="Wave 0 stub")
def test_observations_sorted_desc():
    """get_observations_timeline() returns rows sorted by observed_date descending."""
    from unittest.mock import MagicMock, patch
    from services.patient_query import get_observations_timeline

    rows = [
        {"normalized_analyte": "hemoglobina", "observed_date": "2025-03-01", "value_str": "13.5", "unit": "g/dL", "reference_range": None, "flag": None, "raw_analyte": "Hemoglobina", "document_id": "d1", "needs_review": False},
        {"normalized_analyte": "hemoglobina", "observed_date": "2025-06-15", "value_str": "14.0", "unit": "g/dL", "reference_range": None, "flag": None, "raw_analyte": "Hemoglobina", "document_id": "d2", "needs_review": False},
        {"normalized_analyte": "hemoglobina", "observed_date": "2025-01-10", "value_str": "12.8", "unit": "g/dL", "reference_range": None, "flag": None, "raw_analyte": "Hemoglobina", "document_id": "d3", "needs_review": False},
    ]

    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.execute.return_value.data = rows

    with patch("services.patient_query._get_client", return_value=mock_client):
        result = get_observations_timeline("user1", "hemoglobina")

    assert len(result) == 3
    dates = [r["observed_at"] for r in result]
    assert dates == sorted(dates, reverse=True)


@pytest.mark.skip(reason="Wave 0 stub")
def test_observations_date_filter():
    """get_observations_timeline() applies gte/lte filters when date_from/date_to are provided."""
    from unittest.mock import MagicMock, patch, call
    from services.patient_query import get_observations_timeline

    mock_execute = MagicMock()
    mock_execute.data = []

    # Build a mock chain that records all method calls
    mock_chain = MagicMock()
    mock_chain.execute.return_value = mock_execute
    mock_chain.gte.return_value = mock_chain
    mock_chain.lte.return_value = mock_chain

    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value = mock_chain

    with patch("services.patient_query._get_client", return_value=mock_client):
        get_observations_timeline("user1", "hemoglobina", date_from="2025-06-01", date_to="2025-12-31")

    # Verify gte and lte were called on the chain
    mock_chain.gte.assert_called_once_with("observed_date", "2025-06-01")
    mock_chain.lte.assert_called_once_with("observed_date", "2025-12-31")


@pytest.mark.skip(reason="Wave 0 stub")
def test_value_num_parsing():
    """_enrich_observation() derives value_num from value_str via float() cast."""
    from services.patient_query import _enrich_observation

    row_numeric = {"value_str": "5.7", "unit": "mmol/L", "reference_range": None, "flag": None, "raw_analyte": "Glicose", "normalized_analyte": "glicose", "observed_date": "2025-01-01", "document_id": "d1", "needs_review": False}
    result_numeric = _enrich_observation(row_numeric)
    assert result_numeric["value_num"] == 5.7

    row_text = {"value_str": "positivo", "unit": None, "reference_range": None, "flag": None, "raw_analyte": "HBsAg", "normalized_analyte": "hbsag", "observed_date": "2025-01-01", "document_id": "d1", "needs_review": False}
    result_text = _enrich_observation(row_text)
    assert result_text["value_num"] is None


@pytest.mark.skip(reason="Wave 0 stub")
def test_ref_range_parsing():
    """_enrich_observation() parses ref_low/ref_high from reference_range string."""
    from services.patient_query import _enrich_observation

    base = {"value_str": "4.2", "unit": "g/dL", "flag": None, "raw_analyte": "Hb", "normalized_analyte": "hb", "observed_date": "2025-01-01", "document_id": "d1", "needs_review": False}

    # Valid range
    row_valid = {**base, "reference_range": "3.5-5.0"}
    result = _enrich_observation(row_valid)
    assert result["ref_low"] == 3.5
    assert result["ref_high"] == 5.0

    # None range
    row_none = {**base, "reference_range": None}
    result = _enrich_observation(row_none)
    assert result["ref_low"] is None
    assert result["ref_high"] is None

    # Non-numeric range
    row_text = {**base, "reference_range": "negativo"}
    result = _enrich_observation(row_text)
    assert result["ref_low"] is None
    assert result["ref_high"] is None


@pytest.mark.skip(reason="Wave 0 stub")
def test_patient_summary_shape():
    """get_patient_summary() returns dict with all required keys."""
    from unittest.mock import MagicMock, patch
    from services.patient_query import get_patient_summary

    mock_client = MagicMock()
    # Return empty lists for all table queries
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
    mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
    mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value.data = []

    with patch("services.patient_query._get_client", return_value=mock_client):
        result = get_patient_summary("user1")

    assert result is not None
    assert "user_id" in result
    assert "active_conditions" in result
    assert "current_medications" in result
    assert "allergies" in result
    assert "latest_labs" in result
    assert result["user_id"] == "user1"


@pytest.mark.skip(reason="Wave 0 stub")
def test_latest_labs_dedup():
    """_query_latest_labs() deduplicates by normalized_analyte keeping the most recent row."""
    from unittest.mock import MagicMock
    from services.patient_query import _query_latest_labs

    rows = [
        {"normalized_analyte": "hemoglobina", "raw_analyte": "Hemoglobina", "value_str": "14.0", "unit": "g/dL", "reference_range": None, "flag": None, "needs_review": False, "observed_date": "2025-06-15", "document_id": "d2"},
        {"normalized_analyte": "hemoglobina", "raw_analyte": "Hemoglobina", "value_str": "13.5", "unit": "g/dL", "reference_range": None, "flag": None, "needs_review": False, "observed_date": "2025-03-01", "document_id": "d1"},
        {"normalized_analyte": "hemoglobina", "raw_analyte": "Hemoglobina", "value_str": "12.8", "unit": "g/dL", "reference_range": None, "flag": None, "needs_review": False, "observed_date": "2025-01-10", "document_id": "d3"},
    ]

    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value.data = rows

    result = _query_latest_labs(mock_client, "user1")

    assert len(result) == 1
    assert result[0]["observed_at"] == "2025-06-15"


@pytest.mark.skip(reason="Wave 0 stub")
def test_soft_fail_returns_none():
    """get_patient_summary() returns None when _get_client() raises an exception."""
    from unittest.mock import patch
    from services.patient_query import get_patient_summary

    with patch("services.patient_query._get_client", side_effect=Exception("connection error")):
        result = get_patient_summary("user1")

    assert result is None
