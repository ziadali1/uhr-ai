"""
Unit tests for migrate_health_entries.py — STORE-04 migration.

Tests cover:
  - All 4 HealthEntryType mappings via _map_entry
  - Inactive entries included (not filtered out)
  - Dry-run mode does not call upsert
"""
import sys
import os
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from models.health import HealthEntry, HealthEntryType
from scripts.migrate_health_entries import _map_entry, run_migration


def _make_entry(
    entry_type: HealthEntryType,
    name: str,
    details: str | None = None,
    active: bool = True,
) -> HealthEntry:
    return HealthEntry(
        id="entry-1",
        user_id="user-1",
        entry_type=entry_type,
        name=name,
        details=details,
        started_at=None,
        ended_at=None,
        active=active,
        created_at=datetime.now(timezone.utc),
    )


# ── _map_entry tests ─────────────────────────────────────────────────────────

def test_medication_current_maps_to_active():
    entry = _make_entry(HealthEntryType.medication_current, "Metformina", details="500mg")
    table, row = _map_entry(entry, "user-1")
    assert table == "patient_medications"
    assert row["raw_medication"] == "Metformina"
    assert row["normalized_medication"] == "metformina"
    assert row["dose"] == "500mg"
    assert row["status"] == "active"
    assert row["document_id"] is None


def test_medication_past_maps_to_stopped():
    entry = _make_entry(HealthEntryType.medication_past, "Amoxicilina")
    table, row = _map_entry(entry, "user-1")
    assert table == "patient_medications"
    assert row["status"] == "stopped"
    assert row["document_id"] is None


def test_complaint_maps_to_condition():
    entry = _make_entry(HealthEntryType.complaint, "Dor de cabeca", details="frequente")
    table, row = _map_entry(entry, "user-1")
    assert table == "patient_conditions"
    assert row["raw_condition"] == "Dor de cabeca"
    assert row["normalized_condition"] == "dor de cabeca"
    assert row["clinical_status"] == "active"
    assert row["verification_status"] is None
    assert row["document_id"] is None


def test_allergy_maps_to_allergy():
    entry = _make_entry(HealthEntryType.allergy, "Penicilina", details="urticaria")
    table, row = _map_entry(entry, "user-1")
    assert table == "patient_allergies"
    assert row["raw_allergen"] == "Penicilina"
    assert row["normalized_allergen"] == "penicilina"
    assert row["reaction"] == "urticaria"
    assert row["document_id"] is None


def test_inactive_entry_is_migrated():
    """Inactive entries (active=False) must NOT be filtered out — zero data loss."""
    inactive_entry = _make_entry(
        HealthEntryType.medication_current, "Ibuprofeno", active=False
    )
    mock_client = MagicMock()
    mock_select = mock_client.table.return_value.select.return_value
    mock_select.eq.return_value.execute.return_value.data = [
        {
            "id": "entry-1",
            "user_id": "user-1",
            "entry_type": "medication_current",
            "name": "Ibuprofeno",
            "details": None,
            "started_at": None,
            "ended_at": None,
            "active": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    ]
    with patch("scripts.migrate_health_entries._get_client", return_value=mock_client):
        result = run_migration("user-1", dry_run=False)
    assert result["total"] >= 1
    assert result["migrated"] >= 1


def test_dry_run_does_not_call_upsert():
    """Dry-run mode returns counts but must NOT call client.table().upsert()."""
    mock_client = MagicMock()
    mock_select = mock_client.table.return_value.select.return_value
    mock_select.eq.return_value.execute.return_value.data = [
        {
            "id": "entry-2",
            "user_id": "user-1",
            "entry_type": "complaint",
            "name": "Cefaleia",
            "details": None,
            "started_at": None,
            "ended_at": None,
            "active": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    ]
    with patch("scripts.migrate_health_entries._get_client", return_value=mock_client):
        result = run_migration("user-1", dry_run=True)

    # upsert must never have been called
    mock_client.table.return_value.upsert.assert_not_called()
    assert result["total"] >= 1
