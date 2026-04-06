---
phase: 03-migration-and-backfill
plan: "02"
subsystem: backend/scripts
tags: [backfill, patient-tables, STORE-05, tdd, migration]
dependency_graph:
  requires:
    - 02-02  # patient_store.promote_to_patient_tables
    - 02-01  # patient table schema (patient_observations, patient_conditions, etc.)
  provides:
    - STORE-05 backfill script for pre-Phase-2 documents
  affects:
    - backend/scripts/backfill_patient_tables.py
    - backend/tests/scripts/test_backfill_patient_tables.py
tech_stack:
  added: []
  patterns:
    - thin wrapper pattern (no reimplementation of logic from Phase 2)
    - TDD (RED → GREEN) with unittest.mock.patch
    - argparse CLI with dry-run gate
key_files:
  created:
    - backend/scripts/backfill_patient_tables.py
    - backend/tests/scripts/__init__.py
    - backend/tests/scripts/test_backfill_patient_tables.py
  modified: []
decisions:
  - "Backfill script is intentionally thin: delegates all logic to list_by_user() and promote_to_patient_tables() without reimplementation"
  - "Error counting per-doc (not per-exception) so one failure in a doc does not abort the entire backfill"
  - "dry_run increments promoted counter for eligible docs to give accurate preview of what a live run would do"
metrics:
  duration: "1 min"
  completed_date: "2026-04-06"
  tasks_completed: 1
  files_changed: 3
requirements_satisfied: [STORE-05]
---

# Phase 03 Plan 02: Backfill Patient Tables — Summary

Thin CLI script that promotes structured_result from all pre-Phase-2 documents into patient tables, closing the gap for docs that were uploaded before the Phase 2 wiring was live.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Create backfill_patient_tables.py with promote loop and dry-run | 0f02b54 | backend/scripts/backfill_patient_tables.py, backend/tests/scripts/test_backfill_patient_tables.py |

## What Was Built

`backend/scripts/backfill_patient_tables.py` — a one-shot migration script that:

- Calls `list_by_user(user_id)` from `supabase_store` to fetch all documents
- Iterates each document: skips those with `structured_result=None`, calls `promote_to_patient_tables()` for those with data
- Supports `--dry-run` to preview what would be promoted without writing to DB
- Supports `--verbose` for per-document OK/SKIP status lines
- Counts total/skipped/promoted/errors and prints summary
- Includes `verify_completeness(user_id)` which queries all 5 patient tables and prints counts (activated via `--verify`)
- `load_dotenv()` called before any local imports so `.env` is read in all run modes

`backend/tests/scripts/test_backfill_patient_tables.py` — 4 unit tests covering:
1. `test_promotes_doc_with_structured_result` — verifies correct args passed to promote
2. `test_null_structured_result_skipped` — verifies promote not called, skipped=1
3. `test_dry_run_does_not_call_promote` — verifies no DB writes, promoted count correct
4. `test_error_in_promote_is_counted` — verifies error isolation, script continues to next doc

## Verification

```
python -m pytest tests/scripts/test_backfill_patient_tables.py -v
# 4 passed in 0.74s

python -m pytest tests/ -v
# 52 passed in 0.78s (no regressions)
```

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all logic is wired. `verify_completeness()` makes live Supabase calls and requires a live DB (expected behavior for a migration script). Unit tests mock at the service boundary.

## Self-Check: PASSED

- FOUND: backend/scripts/backfill_patient_tables.py
- FOUND: backend/tests/scripts/test_backfill_patient_tables.py
- FOUND: commit 0f02b54
