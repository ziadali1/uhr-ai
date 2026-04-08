"""Wave 0 stubs for emergency.py refactor.

Tests verify that build_emergency_profile() queries patient tables
instead of using list_by_user() from document_store.

All tests are skipped (Wave 0) — will be unskipped in Plan 02 when
emergency.py is refactored.
"""
import pytest


@pytest.mark.skip(reason="Wave 0 stub")
def test_queries_patient_tables():
    """build_emergency_profile() queries patient_conditions, patient_medications, patient_allergies."""
    from unittest.mock import MagicMock, patch
    from services.emergency import build_emergency_profile

    mock_client = MagicMock()
    # Return empty data for all patient table queries
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
    mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []

    with patch("services.emergency._get_client", return_value=mock_client):
        build_emergency_profile("user1")

    table_calls = [c[0][0] for c in mock_client.table.call_args_list]
    assert "patient_conditions" in table_calls, "Expected query on patient_conditions"
    assert "patient_medications" in table_calls, "Expected query on patient_medications"
    assert "patient_allergies" in table_calls, "Expected query on patient_allergies"


@pytest.mark.skip(reason="Wave 0 stub")
def test_soft_fail_on_table_error():
    """build_emergency_profile() returns EmergencyProfile with empty lists when _get_client() raises."""
    from unittest.mock import patch
    from services.emergency import build_emergency_profile
    from models.emergency import EmergencyProfile

    with patch("services.emergency._get_client", side_effect=Exception("DB error")):
        result = build_emergency_profile("user1")

    assert result is not None, "Expected EmergencyProfile, not None"
    assert isinstance(result, EmergencyProfile)
    assert result.allergies == []
    assert result.active_medications == []
    assert result.active_conditions == []
