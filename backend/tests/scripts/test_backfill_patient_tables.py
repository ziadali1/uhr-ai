"""
Unit tests for backfill_patient_tables.py (STORE-05).

Tests mock supabase_store.list_by_user and patient_store.promote_to_patient_tables.
"""
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest


def _make_doc(doc_id: str, has_sr: bool = True):
    """Create a mock DocumentDetail for testing.

    Args:
        doc_id: document identifier
        has_sr: if True, structured_result is set; if False, it is None
    """
    doc = MagicMock()
    doc.document_id = doc_id
    doc.user_id = "user-1"
    doc.upload_date = datetime(2025, 1, 15, tzinfo=timezone.utc)
    if has_sr:
        sr = MagicMock()
        sr.document_family = "structured_lab"
        doc.structured_result = sr
    else:
        doc.structured_result = None
    return doc


class TestRunBackfill:
    """Tests for run_backfill() in backfill_patient_tables."""

    def test_promotes_doc_with_structured_result(self):
        """Given a DocumentDetail with structured_result != None,
        run_backfill calls promote_to_patient_tables with correct args."""
        doc = _make_doc("doc-1", has_sr=True)

        with patch(
            "scripts.backfill_patient_tables.list_by_user", return_value=[doc]
        ) as mock_list, patch(
            "scripts.backfill_patient_tables.promote_to_patient_tables"
        ) as mock_promote:
            from scripts.backfill_patient_tables import run_backfill

            result = run_backfill(user_id="user-1")

            mock_list.assert_called_once_with("user-1")
            mock_promote.assert_called_once_with(
                doc_id="doc-1",
                user_id="user-1",
                structured_result=doc.structured_result,
                upload_date="2025-01-15",
            )
            assert result["total"] == 1
            assert result["promoted"] == 1
            assert result["skipped"] == 0
            assert result["errors"] == 0

    def test_null_structured_result_skipped(self):
        """Given a DocumentDetail with structured_result=None,
        run_backfill skips it (promote_to_patient_tables NOT called)
        and summary shows skipped=1."""
        doc = _make_doc("doc-null", has_sr=False)

        with patch(
            "scripts.backfill_patient_tables.list_by_user", return_value=[doc]
        ), patch(
            "scripts.backfill_patient_tables.promote_to_patient_tables"
        ) as mock_promote:
            from scripts.backfill_patient_tables import run_backfill

            result = run_backfill(user_id="user-1")

            mock_promote.assert_not_called()
            assert result["skipped"] == 1
            assert result["promoted"] == 0
            assert result["errors"] == 0

    def test_dry_run_does_not_call_promote(self):
        """run_backfill(dry_run=True) does NOT call promote_to_patient_tables,
        returns promoted count based on eligible docs."""
        doc_with_sr = _make_doc("doc-sr", has_sr=True)
        doc_no_sr = _make_doc("doc-no-sr", has_sr=False)

        with patch(
            "scripts.backfill_patient_tables.list_by_user",
            return_value=[doc_with_sr, doc_no_sr],
        ), patch(
            "scripts.backfill_patient_tables.promote_to_patient_tables"
        ) as mock_promote:
            from scripts.backfill_patient_tables import run_backfill

            result = run_backfill(user_id="user-1", dry_run=True)

            mock_promote.assert_not_called()
            assert result["promoted"] == 1  # only eligible docs counted
            assert result["skipped"] == 1
            assert result["total"] == 2
            assert result["errors"] == 0

    def test_error_in_promote_is_counted(self):
        """If promote_to_patient_tables raises Exception,
        summary shows errors=1 and script continues to next doc."""
        doc1 = _make_doc("doc-err", has_sr=True)
        doc2 = _make_doc("doc-ok", has_sr=True)

        call_count = 0

        def side_effect(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("DB connection failed")

        with patch(
            "scripts.backfill_patient_tables.list_by_user", return_value=[doc1, doc2]
        ), patch(
            "scripts.backfill_patient_tables.promote_to_patient_tables",
            side_effect=side_effect,
        ):
            from scripts.backfill_patient_tables import run_backfill

            result = run_backfill(user_id="user-1")

            assert result["errors"] == 1
            assert result["promoted"] == 1  # doc2 succeeded
            assert result["total"] == 2
            assert result["skipped"] == 0
