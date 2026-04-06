"""
Backfill script: promote existing document structured_results into patient tables.

STORE-05 — Documents uploaded before Phase 2 wiring have structured_result
but no patient table rows. This script closes that gap so ALL documents
contribute to the patient profile.

Usage:
    python -m scripts.backfill_patient_tables --user-id <UUID> [--dry-run] [--verbose] [--verify]

Design: intentionally thin — reuses list_by_user() and promote_to_patient_tables()
from Phase 2 without reimplementing any logic.
"""

import sys
import os

# Must be before any local imports so that env vars are available
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from dotenv import load_dotenv
load_dotenv()

import argparse
import logging

from services.supabase_store import list_by_user
from services.patient_store import promote_to_patient_tables

_log = logging.getLogger(__name__)


def run_backfill(
    user_id: str,
    dry_run: bool = False,
    verbose: bool = False,
) -> dict:
    """Iterate all documents for user_id and promote structured_result to patient tables.

    Args:
        user_id: Supabase user UUID to backfill.
        dry_run: If True, report what would be promoted without writing to DB.
        verbose: If True, print per-document status messages.

    Returns:
        dict with keys: total, skipped, promoted, errors
    """
    docs = list_by_user(user_id)
    total = len(docs)
    skipped = 0
    promoted = 0
    errors = 0

    for doc in docs:
        # Skip documents with no structured extraction
        if doc.structured_result is None:
            skipped += 1
            if verbose:
                print(f"SKIP {doc.document_id} -- no structured_result")
            continue

        # Dry-run: count eligible docs without writing
        if dry_run:
            print(
                f"DRY-RUN would promote {doc.document_id}"
                f" ({doc.structured_result.document_family})"
            )
            promoted += 1
            continue

        # Live run: call promote and count errors
        try:
            promote_to_patient_tables(
                doc_id=doc.document_id,
                user_id=user_id,
                structured_result=doc.structured_result,
                upload_date=doc.upload_date.strftime("%Y-%m-%d"),
            )
            promoted += 1
            if verbose:
                print(f"OK {doc.document_id}")
        except Exception as exc:
            errors += 1
            print(f"ERROR {doc.document_id}: {exc}")

    return {"total": total, "skipped": skipped, "promoted": promoted, "errors": errors}


def verify_completeness(user_id: str) -> None:
    """Print counts of documents vs patient table rows for a given user.

    Useful to confirm that backfill reached all expected tables.
    """
    from services.supabase_store import _get_client

    client = _get_client()

    # Documents with non-null structured_result (eligible for promotion)
    eligible = (
        client.table("documents")
        .select("id", count="exact")
        .eq("user_id", user_id)
        .not_.is_("structured_result", "null")
        .execute()
    )

    obs = (
        client.table("patient_observations")
        .select("id", count="exact")
        .eq("user_id", user_id)
        .execute()
    )
    cond = (
        client.table("patient_conditions")
        .select("id", count="exact")
        .eq("user_id", user_id)
        .execute()
    )
    meds = (
        client.table("patient_medications")
        .select("id", count="exact")
        .eq("user_id", user_id)
        .execute()
    )
    allergies = (
        client.table("patient_allergies")
        .select("id", count="exact")
        .eq("user_id", user_id)
        .execute()
    )
    imaging = (
        client.table("patient_imaging_findings")
        .select("id", count="exact")
        .eq("user_id", user_id)
        .execute()
    )

    print("\n--- Completeness Report ---")
    print(f"  Documents with structured_result: {eligible.count}")
    print(f"  patient_observations:             {obs.count}")
    print(f"  patient_conditions:               {cond.count}")
    print(f"  patient_medications:              {meds.count}")
    print(f"  patient_allergies:                {allergies.count}")
    print(f"  patient_imaging_findings:         {imaging.count}")
    print("---------------------------\n")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    parser = argparse.ArgumentParser(
        description="Backfill patient tables from document structured_results."
    )
    parser.add_argument("--user-id", required=True, help="Supabase user UUID to backfill")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would be promoted without writing to DB",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print per-document status during backfill",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Print completeness counts after backfill",
    )
    args = parser.parse_args()

    summary = run_backfill(
        user_id=args.user_id,
        dry_run=args.dry_run,
        verbose=args.verbose,
    )

    mode = "DRY-RUN" if args.dry_run else "LIVE"
    print(f"\n[{mode}] Backfill complete for user {args.user_id}")
    print(f"  Total:    {summary['total']}")
    print(f"  Skipped:  {summary['skipped']}")
    print(f"  Promoted: {summary['promoted']}")
    print(f"  Errors:   {summary['errors']}")

    if args.verify:
        verify_completeness(args.user_id)
