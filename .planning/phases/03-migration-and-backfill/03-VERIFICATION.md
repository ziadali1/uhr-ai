---
phase: 03-migration-and-backfill
verified: 2026-04-06T19:30:00Z
status: human_needed
score: 9/9 must-haves verified (automated); 2 items require live DB confirmation
re_verification: false
human_verification:
  - test: "Confirm health_entries table still has 2 rows in Supabase Dashboard"
    expected: "SELECT COUNT(*) FROM health_entries returns 2 (table preserved, not deleted)"
    why_human: "Live DB state cannot be verified without credentials; SUMMARY claims 2 rows preserved"
  - test: "Confirm patient_medications has at least 1 row for the user after migration"
    expected: "SELECT COUNT(*) FROM patient_medications WHERE user_id = '<user>' returns >= 1 (rivotril 2mg entry)"
    why_human: "Live DB state cannot be verified without credentials; SUMMARY claims 1 row migrated"
---

# Phase 3: Migration and Backfill Verification Report

**Phase Goal:** Bring all existing data into the new model — zero data left behind.
**Verified:** 2026-04-06T19:30:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | health_entries medication_current maps to patient_medications status='active' | VERIFIED | test_medication_current_maps_to_active PASSES; _map_entry returns status="active" |
| 2 | health_entries medication_past maps to patient_medications status='stopped' | VERIFIED | test_medication_past_maps_to_stopped PASSES; _map_entry returns status="stopped" |
| 3 | health_entries complaint maps to patient_conditions clinical_status='active' | VERIFIED | test_complaint_maps_to_condition PASSES; _map_entry returns clinical_status="active" |
| 4 | health_entries allergy maps to patient_allergies with reaction from details | VERIFIED | test_allergy_maps_to_allergy PASSES; _map_entry returns reaction=entry.details |
| 5 | Inactive entries (active=False) are migrated — zero data loss | VERIFIED | test_inactive_entry_is_migrated PASSES; direct table query bypasses active=True filter; _log comment at line 113 confirms intent |
| 6 | Dry-run mode reports without writing (both scripts) | VERIFIED | test_dry_run_does_not_call_upsert PASSES; test_dry_run_does_not_call_promote PASSES |
| 7 | Documents with structured_result are promoted via promote_to_patient_tables | VERIFIED | test_promotes_doc_with_structured_result PASSES; backfill calls promote_to_patient_tables with correct args |
| 8 | Documents with structured_result=None are skipped without error | VERIFIED | test_null_structured_result_skipped PASSES; promote never called, skipped counter incremented |
| 9 | Scripts are idempotent — upsert ON CONFLICT prevents duplicates | VERIFIED | migrate_health_entries.py line 149: upsert(row, on_conflict=_CONFLICT_COLS[table]); backfill inherits idempotency from promote_to_patient_tables |

**Score:** 9/9 automated truths verified

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/scripts/migrate_health_entries.py` | STORE-04 migration script | VERIFIED | 199 lines; contains def _map_entry, def run_migration, direct health_entries query, dry-run support, argparse with --dry-run |
| `backend/scripts/backfill_patient_tables.py` | STORE-05 backfill script | VERIFIED | 185 lines; contains def run_backfill, def verify_completeness, imports list_by_user and promote_to_patient_tables, --dry-run and --verify flags |
| `backend/tests/scripts/__init__.py` | Package init | VERIFIED | Exists (empty, as required) |
| `backend/tests/scripts/test_migrate_health_entries.py` | 6 unit tests for STORE-04 | VERIFIED | Contains all 6 required test functions including test_inactive_entry_is_migrated and test_dry_run_does_not_call_upsert; 6/6 PASS |
| `backend/tests/scripts/test_backfill_patient_tables.py` | 4 unit tests for STORE-05 | VERIFIED | Contains all 4 required test functions including test_null_structured_result_skipped and test_dry_run_does_not_call_promote; 4/4 PASS |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| migrate_health_entries.py | health_entries table | client.table("health_entries").select("*").eq("user_id", user_id) | WIRED | Lines 116-119: direct multi-line chained query; explicitly avoids health_store.list_by_user() |
| migrate_health_entries.py | patient_medications, patient_conditions, patient_allergies | client.table(table).upsert(row, on_conflict=_CONFLICT_COLS[table]).execute() | WIRED | Line 149: called in non-dry-run branch; _CONFLICT_COLS dict maps all 3 tables |
| backfill_patient_tables.py | services/supabase_store.py | from services.supabase_store import list_by_user; docs = list_by_user(user_id) | WIRED | Line 26 import, line 47 call; test mocks confirm correct import path |
| backfill_patient_tables.py | services/patient_store.py | from services.patient_store import promote_to_patient_tables; called per doc | WIRED | Line 27 import, lines 72-76 call with doc_id, user_id, structured_result, upload_date |

---

## Data-Flow Trace (Level 4)

Scripts are migration/backfill utilities, not components that render dynamic data to a UI. Data flow is:
- Source: live Supabase DB (health_entries and documents tables)
- Sink: patient_medications, patient_conditions, patient_allergies tables
- The actual data transformation is tested at unit level via mocks.
- Live end-to-end data flow is confirmed by SUMMARY 03-03 execution logs (1 health_entry promoted, 3 documents backfilled, errors=0, idempotency verified by second run). Cannot be re-verified programmatically without live DB credentials — routed to human verification.

---

## Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| 6 STORE-04 unit tests pass | python -m pytest tests/scripts/test_migrate_health_entries.py -v | 6 passed in 0.67s | PASS |
| 4 STORE-05 unit tests pass | python -m pytest tests/scripts/test_backfill_patient_tables.py -v | 4 passed in 0.67s | PASS |
| Full suite — no regressions | python -m pytest tests/ -v | 58 passed in 0.90s | PASS |
| migrate_health_entries.py does NOT use list_by_user() for querying | grep -c "list_by_user" migrate_health_entries.py (functional call) | 0 functional calls (comment only) | PASS |
| Script has correct on_conflict upsert | grep on_conflict migrate_health_entries.py | Line 149: upsert(row, on_conflict=_CONFLICT_COLS[table]) | PASS |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| STORE-04 | 03-01, 03-03 | System migrates existing manual health_entries records into new patient tables without data loss | SATISFIED | migrate_health_entries.py: all 4 entry_type mappings implemented and tested; direct query includes inactive entries; upsert idempotency; 6/6 unit tests pass; live migration documented in 03-03-SUMMARY (1 row promoted, errors=0) |
| STORE-05 | 03-02, 03-03 | System backfills existing documents' structured_result JSONB into new patient tables | SATISFIED | backfill_patient_tables.py: delegates to promote_to_patient_tables for all docs with structured_result; skips nulls; dry-run gate; verify_completeness function; 4/4 unit tests pass; live backfill documented in 03-03-SUMMARY (3 docs promoted, errors=0, idempotency verified) |

No orphaned requirements — REQUIREMENTS.md maps only STORE-04 and STORE-05 to Phase 3, and both plans claim them.

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| 03-VALIDATION.md | 41-45 | All task status fields remain "pending" after execution | Info | Documentation only — no code impact; SUMMARY files contain the actual execution evidence |

No code-level anti-patterns found in migration scripts or test files. No TODOs, FIXMEs, placeholder returns, or hardcoded empty values that flow to rendering.

---

## Human Verification Required

### 1. health_entries Table Preservation

**Test:** In Supabase Dashboard, run `SELECT COUNT(*) FROM health_entries` (or check Table Editor -> health_entries row count).
**Expected:** 2 rows — table exists and was not deleted or truncated by the migration.
**Why human:** Live database state cannot be verified without credentials. SUMMARY 03-03 documents this result but the verifier cannot re-query the live DB.

### 2. Patient Tables Populated After Live Migration

**Test:** In Supabase Dashboard, check:
- `SELECT COUNT(*) FROM patient_medications WHERE user_id = '<user>'` — should return >= 1
- `SELECT COUNT(*) FROM patient_conditions WHERE user_id = '<user>'` — depends on complaint entries
- Optionally run `python scripts/backfill_patient_tables.py --user-id <user> --verify` to see the completeness report
**Expected:** patient_medications has at least 1 row (rivotril 2mg from the migrated health_entry); patient_observations=0 is expected and documented (pre-Phase-1 OCR produced empty observations arrays).
**Why human:** Live database state cannot be verified without credentials. The 03-03-SUMMARY documents the live execution results with specific counts but these must be confirmed against the actual DB.

---

## Gaps Summary

No gaps found. All 9 automated truths are verified by unit tests, artifact inspection, and key link tracing. Both scripts are fully implemented, substantive, wired to their dependencies, and proven by a 58-test suite with zero regressions.

The two human verification items are confirmations of live DB state documented in the SUMMARY, not gaps in implementation. The scripts have the correct logic; the question is only whether the SUMMARY's reported migration counts are accurate.

STORE-04 and STORE-05 are both satisfied by the codebase as it stands.

---

_Verified: 2026-04-06T19:30:00Z_
_Verifier: Claude (gsd-verifier)_
