"""Unit tests for services.patient_store promotion logic.

Covers:
  - All 4 document family promotion paths (lab, clinical, medications, imaging)
  - Alias normalization (with/without alias match)
  - Brazilian date parsing (DD/MM/YYYY, None/fallback, garbage input)
  - Observation dedup: identical no-op, conflict sets needs_review=True
  - Soft-fail: exception in _get_client never propagates
  - Edge cases: None structured_result, unknown family
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from unittest.mock import MagicMock, patch, call

from models.document import (
    StructuredResult,
    StructuredLab,
    LabFinding,
    ClinicalNote,
    MedicationDocument,
    MedicationEntry,
    ImagingReport,
)
from services.patient_store import (
    promote_to_patient_tables,
    _normalize_analyte,
    _parse_br_date,
)


# ── Test helpers ──────────────────────────────────────────────────────────────

def _mock_client():
    """Return a MagicMock that safely chains Supabase-style calls.

    Default behaviour:
    - .table().select().eq().eq().eq().execute().data = [] (no existing observations)
    - .table().select().execute().data = []  (empty alias table)
    - .table().insert/upsert().execute().data = [{"id": "new"}]
    """
    client = MagicMock()
    # No existing rows for observation pre-check (SELECT chain)
    client.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
    # Empty alias table (SELECT without eq chain)
    client.table.return_value.select.return_value.execute.return_value.data = []
    # Insert/upsert succeed
    client.table.return_value.insert.return_value.execute.return_value.data = [{"id": "new"}]
    client.table.return_value.upsert.return_value.execute.return_value.data = [{"id": "new"}]
    return client


def _lab_result(findings, collection_date="15/03/2025"):
    """Build a StructuredResult wrapping a StructuredLab."""
    return StructuredResult(
        document_family="structured_lab",
        structured_data=StructuredLab(
            collection_date=collection_date,
            findings=findings,
        ).model_dump(),
    )


def _clinical_result(diagnoses=None, suspected=None, allergies=None, medications=None):
    """Build a StructuredResult wrapping a ClinicalNote."""
    return StructuredResult(
        document_family="clinical_narrative",
        structured_data=ClinicalNote(
            diagnoses=diagnoses or [],
            suspected_diagnoses=suspected or [],
            allergies=allergies or [],
            medications=medications or [],
        ).model_dump(),
    )


def _medication_result(entries):
    """Build a StructuredResult wrapping a MedicationDocument."""
    return StructuredResult(
        document_family="medication_document",
        structured_data=MedicationDocument(
            medications=entries,
        ).model_dump(),
    )


def _imaging_result(modality="CT", body_region="Tórax", impression="Normal", urgency="routine"):
    """Build a StructuredResult wrapping an ImagingReport."""
    return StructuredResult(
        document_family="imaging_narrative",
        structured_data=ImagingReport(
            modality=modality,
            body_region=body_region,
            impression=impression,
            urgency=urgency,
        ).model_dump(),
    )


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_promote_none_structured_result():
    """structured_result=None → returns immediately, _get_client never called."""
    with patch("services.patient_store._get_client") as mock_get_client:
        promote_to_patient_tables("doc-1", "user-1", None)
        mock_get_client.assert_not_called()


def test_promote_unknown_family():
    """Unknown document_family → no client table operations, no error raised."""
    result = StructuredResult(
        document_family="unknown",
        structured_data={},
    )
    mock_client = _mock_client()
    with patch("services.patient_store._get_client", return_value=mock_client):
        promote_to_patient_tables("doc-1", "user-1", result)
    # No table operations should have been triggered
    mock_client.table.assert_not_called()


def test_promote_does_not_raise_on_exception():
    """Soft-fail (D-04): _get_client raising RuntimeError must not propagate."""
    result = _lab_result([LabFinding(name="Glicose", value="95", unit="mg/dL")])
    with patch("services.patient_store._get_client", side_effect=RuntimeError("DB down")):
        # Must NOT raise — this is the core D-04 contract
        promote_to_patient_tables("doc-1", "user-1", result)


def test_promote_lab_inserts_observations():
    """Lab result with 1 finding → patient_observations insert called."""
    result = _lab_result([LabFinding(name="Glicose", value="95", unit="mg/dL", flag="normal")])
    mock_client = _mock_client()

    with patch("services.patient_store._get_client", return_value=mock_client):
        promote_to_patient_tables("doc-1", "user-1", result)

    # Verify that patient_observations was inserted into
    table_calls = [str(c) for c in mock_client.table.call_args_list]
    obs_calls = [c for c in table_calls if "patient_observations" in c]
    assert len(obs_calls) >= 1, "Expected at least one patient_observations table call"


def test_normalize_analyte_with_alias():
    """Alias lookup: 'Glicose' with alias {'glicose': 'glicose'} → 'glicose'."""
    result = _normalize_analyte("Glicose", {"glicose": "glicose"})
    assert result == "glicose"


def test_normalize_analyte_without_alias():
    """No alias: 'UnknownTest' with empty dict → 'unknowntest' (lowercased)."""
    result = _normalize_analyte("UnknownTest", {})
    assert result == "unknowntest"


def test_duplicate_observation_identical_is_noop():
    """D-01: identical value/unit → no insert (existing row SELECT returns match)."""
    result = _lab_result([LabFinding(name="Glicose", value="95", unit="mg/dL")])
    mock_client = _mock_client()

    # Mock existing row with IDENTICAL value and unit
    existing_row = {"id": "existing-id", "value_str": "95", "unit": "mg/dL"}
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value.data = [existing_row]

    with patch("services.patient_store._get_client", return_value=mock_client):
        promote_to_patient_tables("doc-1", "user-1", result)

    # insert must NOT have been called (it's a no-op)
    mock_client.table.return_value.insert.assert_not_called()


def test_duplicate_observation_conflict_sets_needs_review():
    """D-01: conflicting value → insert NEW row with needs_review=True."""
    result = _lab_result([LabFinding(name="Glicose", value="95", unit="mg/dL")])
    mock_client = _mock_client()

    # Mock existing row with DIFFERENT value (100 vs 95 → conflict)
    existing_row = {"id": "existing-id", "value_str": "100", "unit": "mg/dL"}
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value.data = [existing_row]

    with patch("services.patient_store._get_client", return_value=mock_client):
        promote_to_patient_tables("doc-1", "user-1", result)

    # insert MUST have been called with needs_review=True
    insert_call = mock_client.table.return_value.insert.call_args
    assert insert_call is not None, "Expected insert to be called for conflict row"
    inserted_row = insert_call[0][0]
    assert inserted_row.get("needs_review") is True, (
        f"Expected needs_review=True in conflict row, got: {inserted_row}"
    )


def test_promote_clinical_conditions_and_allergies():
    """Clinical note with diagnoses and allergies → upsert on both tables."""
    result = _clinical_result(diagnoses=["Hipertensão"], allergies=["Dipirona"])
    mock_client = _mock_client()

    with patch("services.patient_store._get_client", return_value=mock_client):
        promote_to_patient_tables("doc-1", "user-1", result)

    table_calls = [c[0][0] for c in mock_client.table.call_args_list]
    assert "patient_conditions" in table_calls, "Expected upsert on patient_conditions"
    assert "patient_allergies" in table_calls, "Expected upsert on patient_allergies"


def test_promote_clinical_suspected_diagnosis():
    """Suspected diagnoses → clinical_status='suspected', verification_status='provisional'."""
    result = _clinical_result(suspected=["Diabetes mellitus tipo 2"])
    mock_client = _mock_client()

    with patch("services.patient_store._get_client", return_value=mock_client):
        promote_to_patient_tables("doc-1", "user-1", result)

    # Find the upsert call on patient_conditions
    upsert_calls = mock_client.table.return_value.upsert.call_args_list
    assert upsert_calls, "Expected at least one upsert call"
    upserted_row = upsert_calls[0][0][0]
    assert upserted_row.get("clinical_status") == "suspected", (
        f"Expected clinical_status='suspected', got: {upserted_row.get('clinical_status')}"
    )
    assert upserted_row.get("verification_status") == "provisional", (
        f"Expected verification_status='provisional', got: {upserted_row.get('verification_status')}"
    )


def test_promote_medications_from_medication_document():
    """MedicationDocument with entries → upsert on patient_medications with dose/route/frequency."""
    entries = [MedicationEntry(name="Metformina", dose="500mg", route="oral", frequency="2x/dia")]
    result = _medication_result(entries)
    mock_client = _mock_client()

    with patch("services.patient_store._get_client", return_value=mock_client):
        promote_to_patient_tables("doc-1", "user-1", result)

    table_calls = [c[0][0] for c in mock_client.table.call_args_list]
    assert "patient_medications" in table_calls, "Expected upsert on patient_medications"

    upsert_calls = mock_client.table.return_value.upsert.call_args_list
    assert upsert_calls, "Expected at least one upsert call for medication"
    upserted_row = upsert_calls[0][0][0]
    assert upserted_row.get("dose") == "500mg"
    assert upserted_row.get("route") == "oral"
    assert upserted_row.get("frequency") == "2x/dia"
    assert upserted_row.get("raw_medication") == "Metformina"


def test_parse_br_date():
    """Date parsing: DD/MM/YYYY → ISO, None+fallback → fallback, garbage → None."""
    assert _parse_br_date("15/03/2025") == "2025-03-15"
    assert _parse_br_date(None, fallback="2025-01-01") == "2025-01-01"
    assert _parse_br_date("garbage") is None
    # Already ISO should also work
    assert _parse_br_date("2025-03-15") == "2025-03-15"
    # None without fallback → None
    assert _parse_br_date(None) is None
