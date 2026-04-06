"""
migrate_health_entries.py — STORE-04

Migrates manual health_entries rows to the structured patient tables:
  health_entries(entry_type=medication_current) -> patient_medications(status='active')
  health_entries(entry_type=medication_past)    -> patient_medications(status='stopped')
  health_entries(entry_type=complaint)          -> patient_conditions(clinical_status='active')
  health_entries(entry_type=allergy)            -> patient_allergies

CRITICAL: Fetches ALL health_entries (including active=False) — zero data loss.
Idempotent via upsert ON CONFLICT on normalized fields.
Supports --dry-run mode for safe inspection.

Usage:
    python scripts/migrate_health_entries.py --user-id <uuid> [--dry-run] [--verbose]
"""
import sys
import os

# Must be BEFORE any local imports so env vars are loaded from .env
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from dotenv import load_dotenv
load_dotenv()

import argparse
import logging
import uuid

from models.health import HealthEntry, HealthEntryType
from services.supabase_store import _get_client
from services.health_store import _row_to_entry

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
_log = logging.getLogger(__name__)

# On-conflict columns per patient table (D-06 idempotency)
_CONFLICT_COLS: dict[str, str] = {
    "patient_medications": "user_id,normalized_medication",
    "patient_conditions":  "user_id,normalized_condition",
    "patient_allergies":   "user_id,normalized_allergen",
}


def _map_entry(entry: HealthEntry, user_id: str) -> tuple[str, dict]:
    """Map a single HealthEntry to (table_name, row_dict) for upsert.

    Returns:
        (table_name, row) where document_id is always None (no source document
        for manual entries).
    """
    if entry.entry_type in (HealthEntryType.medication_current, HealthEntryType.medication_past):
        status = "active" if entry.entry_type == HealthEntryType.medication_current else "stopped"
        row = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "document_id": None,
            "raw_medication": entry.name,
            "normalized_medication": entry.name.strip().lower(),
            "dose": entry.details,
            "route": None,
            "frequency": None,
            "status": status,
        }
        return "patient_medications", row

    elif entry.entry_type == HealthEntryType.complaint:
        row = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "document_id": None,
            "raw_condition": entry.name,
            "normalized_condition": entry.name.strip().lower(),
            "clinical_status": "active",
            "verification_status": None,
        }
        return "patient_conditions", row

    elif entry.entry_type == HealthEntryType.allergy:
        row = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "document_id": None,
            "raw_allergen": entry.name,
            "normalized_allergen": entry.name.strip().lower(),
            "reaction": entry.details,
        }
        return "patient_allergies", row

    else:
        raise ValueError(f"Unknown entry_type: {entry.entry_type}")


def run_migration(
    user_id: str,
    dry_run: bool = False,
    verbose: bool = False,
) -> dict:
    """Run migration for a single user_id.

    Fetches ALL health_entries (not filtered by active) to ensure zero data loss.
    Upserts each entry into the appropriate patient table unless dry_run=True.

    Args:
        user_id: The user whose entries to migrate.
        dry_run: If True, report what would be migrated without writing to DB.
        verbose: If True, log each individual entry.

    Returns:
        dict with keys: total, migrated, errors
    """
    client = _get_client()

    # CRITICAL: Do NOT use health_store.list_by_user() — it filters active=True.
    # Query health_entries directly to include ALL entries (active and inactive).
    res = (
        client.table("health_entries")
        .select("*")
        .eq("user_id", user_id)
        .execute()
    )
    rows = res.data or []

    total = len(rows)
    migrated = 0
    errors = 0

    for raw_row in rows:
        try:
            entry = _row_to_entry(raw_row)
            table, row = _map_entry(entry, user_id)

            if dry_run:
                if verbose:
                    _log.info(
                        "[DRY-RUN] Would upsert into %s: %s -> %s",
                        table,
                        entry.name,
                        row.get("status") or row.get("clinical_status") or "allergy",
                    )
                migrated += 1
            else:
                if verbose:
                    _log.info(
                        "Upserting %s into %s (conflict: %s)",
                        entry.name,
                        table,
                        _CONFLICT_COLS[table],
                    )
                client.table(table).upsert(row, on_conflict=_CONFLICT_COLS[table]).execute()
                migrated += 1

        except Exception as exc:
            _log.error(
                "Failed to migrate entry id=%s entry_type=%s: %s",
                raw_row.get("id"),
                raw_row.get("entry_type"),
                exc,
            )
            errors += 1

    return {"total": total, "migrated": migrated, "errors": errors}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Migrate health_entries to patient tables (STORE-04)."
    )
    parser.add_argument(
        "--user-id",
        required=True,
        help="User UUID whose health_entries will be migrated.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Report what would be migrated without writing to DB.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        default=False,
        help="Log each individual entry during migration.",
    )
    args = parser.parse_args()

    summary = run_migration(
        user_id=args.user_id,
        dry_run=args.dry_run,
        verbose=args.verbose,
    )

    mode = "DRY-RUN" if args.dry_run else "LIVE"
    print(
        f"\n[{mode}] Migration complete for user {args.user_id}:\n"
        f"  Total entries found : {summary['total']}\n"
        f"  Migrated            : {summary['migrated']}\n"
        f"  Errors              : {summary['errors']}\n"
    )
