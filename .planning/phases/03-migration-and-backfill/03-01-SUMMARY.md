---
phase: 03-migration-and-backfill
plan: 01
subsystem: backend/scripts
tags: [migration, health-entries, patient-tables, tdd, store-04]
dependency_graph:
  requires:
    - backend/services/health_store.py (_row_to_entry)
    - backend/services/supabase_store.py (_get_client)
    - backend/models/health.py (HealthEntry, HealthEntryType)
    - patient_medications, patient_conditions, patient_allergies tables
  provides:
    - backend/scripts/migrate_health_entries.py (STORE-04 migration)
    - backend/tests/scripts/test_migrate_health_entries.py (6 unit tests)
  affects:
    - Phase 5+ routing (patient data now queryable from one place)
    - Phase 6 timeline (all manual entries visible as longitudinal data)
tech_stack:
  added: []
  patterns:
    - TDD (RED → GREEN commit cycle)
    - upsert ON CONFLICT for idempotency (D-06 pattern from patient_store.py)
    - dotenv loaded before service imports (main.py pattern)
key_files:
  created:
    - backend/scripts/migrate_health_entries.py
    - backend/tests/scripts/__init__.py
    - backend/tests/scripts/test_migrate_health_entries.py
  modified: []
decisions:
  - "Direct health_entries table query (not health_store.list_by_user) to include active=False entries — zero data loss"
  - "started_at/ended_at intentionally dropped — patient_medications has no date range columns (open question #2 in research)"
  - "document_id=None for all manual entries — no source document"
metrics:
  duration: "2min"
  completed: "2026-04-06"
  tasks_completed: 1
  tasks_total: 1
  files_created: 3
  files_modified: 0
---

# Phase 3 Plan 1: Health Entries Migration Script (STORE-04) Summary

One-liner: Idempotent migration script mapping all 4 manual HealthEntryType values to patient tables via upsert ON CONFLICT, with dry-run mode and 6 passing unit tests.

## What Was Built

`backend/scripts/migrate_health_entries.py` — CLI migration script that reads all rows from the `health_entries` table for a given user and upserts them into the structured patient tables:

| entry_type           | Target Table        | Key Mapping                   |
|----------------------|---------------------|-------------------------------|
| medication_current   | patient_medications | status='active'               |
| medication_past      | patient_medications | status='stopped'              |
| complaint            | patient_conditions  | clinical_status='active'      |
| allergy              | patient_allergies   | reaction=details              |

All migrated rows have `document_id=None` (no source document for manual entries).

## Key Design Decisions

1. **Direct table query, not `health_store.list_by_user()`**: `list_by_user` filters `active=True` and would silently lose soft-deleted entries. The script queries `health_entries` directly via `client.table("health_entries").select("*").eq("user_id", user_id)` to guarantee zero data loss.

2. **Idempotent via upsert**: Each patient table uses ON CONFLICT on `(user_id, normalized_field)` — safe to re-run without duplicating rows.

3. **Dry-run mode**: `--dry-run` flag reports what would be migrated (counts + verbose logging) without any writes. Required for safe pre-flight inspection.

4. **`load_dotenv()` before service imports**: Follows `main.py` pattern — env vars must be loaded before `_get_client()` is called.

5. **started_at/ended_at dropped intentionally**: `patient_medications` has no date-range columns. Documented in 03-RESEARCH.md open question #2.

## Tests

6 unit tests in `backend/tests/scripts/test_migrate_health_entries.py`:

| Test | What It Verifies |
|------|-----------------|
| test_medication_current_maps_to_active | status='active', document_id=None, normalized name |
| test_medication_past_maps_to_stopped | status='stopped', document_id=None |
| test_complaint_maps_to_condition | clinical_status='active', verification_status=None |
| test_allergy_maps_to_allergy | reaction=details, normalized_allergen |
| test_inactive_entry_is_migrated | active=False entries appear in migration output |
| test_dry_run_does_not_call_upsert | mock upsert never called in dry_run=True mode |

Full suite: 54/54 tests pass (48 pre-existing + 6 new), zero regressions.

## Deviations from Plan

None — plan executed exactly as written.

## Commits

| Commit | Type | Description |
|--------|------|-------------|
| 3b4dce4 | test | Add failing tests for health_entries migration (RED) |
| 0e3f755 | feat | Implement health_entries migration script (GREEN) |

## Self-Check: PASSED

- backend/scripts/migrate_health_entries.py — FOUND
- backend/tests/scripts/test_migrate_health_entries.py — FOUND
- .planning/phases/03-migration-and-backfill/03-01-SUMMARY.md — FOUND
- Commits 3b4dce4 and 0e3f755 — FOUND in git log
