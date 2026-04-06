---
phase: 02-longitudinal-patient-data-model
plan: 02
subsystem: database
tags: [supabase, pydantic, patient-data, promotion, dedup, upsert, pytest]

# Dependency graph
requires:
  - phase: 02-01
    provides: "Pydantic patient models (PatientObservation, PatientCondition, PatientMedication, PatientAllergy, PatientImagingFinding) + Supabase migration SQL for 6 patient tables"
  - phase: 01-adaptive-text-extraction
    provides: "StructuredResult with structured_data populated by LLM extraction pipeline"
provides:
  - "promote_to_patient_tables() public entry point dispatching to 4 family-specific functions"
  - "_promote_lab() with alias lookup, Brazilian date parsing, observation conflict detection"
  - "_promote_clinical() upserting conditions (active/suspected), allergies, medications from ClinicalNote"
  - "_promote_medications() upserting MedicationEntry with dose/route/frequency"
  - "_promote_imaging() inserting imaging findings (no dedup key per D-13)"
  - "_promote_observation() with SELECT pre-check for D-01 identical/conflict handling"
  - "_load_aliases() one-call-per-document cache returning {raw_name_lower: canonical_name}"
  - "_normalize_analyte() case-insensitive alias lookup, fallback to lowercased raw name"
  - "_parse_br_date() handling DD/MM/YYYY and ISO formats with upload_date fallback"
  - "12 unit tests covering all promotion paths, dedup, conflict detection, soft-fail"
affects:
  - phase: 02-03
  - upload-pipeline
  - patient-query
  - clinical-reasoning

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Promotion dispatch: structured_result.document_family → family-specific _promote_* function"
    - "Soft-fail wrapper: try/except in promote_to_patient_tables logs and swallows all exceptions (D-04/D-07)"
    - "Observation conflict detection: SELECT pre-check → identical=no-op, conflict=insert new row with needs_review=True (D-01)"
    - "Alias per-call cache: _load_aliases(client) called once per lab document, not per finding (anti N+1)"
    - "Upsert pattern: on_conflict= with no spaces between column names (Pitfall 4)"

key-files:
  created:
    - backend/services/patient_store.py
    - backend/tests/patient/__init__.py
    - backend/tests/patient/test_patient_store.py
  modified: []

key-decisions:
  - "Observation pre-check uses SELECT then conditional INSERT rather than upsert because D-01 requires storing BOTH conflicting rows (upsert would overwrite the original)"
  - "_load_aliases wrapped in try/except returning {} so promotion still works in dev environments without the analyte_aliases table applied"
  - "Brazilian date fallback to upload_date (not None) ensures concrete observed_date for dedup key — NULL != NULL in SQL would create duplicates on re-upload"

patterns-established:
  - "Pattern: Promotion dispatch loop — map document_family string to _promote_* function, unknown families silently skip"
  - "Pattern: Soft-fail service — top-level try/except in entry point, never re-raises, logs warning with doc_id"

requirements-completed: [STORE-02, STORE-03]

# Metrics
duration: 5min
completed: 2026-04-06
---

# Phase 2 Plan 2: Patient Store Promotion Summary

**patient_store.py with 4 family promotion paths, Brazilian date parsing, analyte alias lookup, D-01 conflict detection, and 12 green unit tests**

## Performance

- **Duration:** 5 min
- **Started:** 2026-04-06T12:39:18Z
- **Completed:** 2026-04-06T12:44:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Implemented complete `services/patient_store.py` with `promote_to_patient_tables()` entry point and 4 family-specific promotion functions
- D-01 conflict detection: SELECT pre-check for observations — identical value/unit is a no-op, conflicting value inserts new row with `needs_review=True`
- 12 unit tests covering all promotion paths, alias normalization, date parsing, dedup, conflict flagging, and soft-fail; full 48-test suite passes with no regression

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement patient_store.py with promotion functions per family** - `8eb0854` (feat)
2. **Task 2: Create unit tests for patient_store promotion logic** - `999944a` (test)

**Plan metadata:** (docs commit below)

_Note: Both tasks used TDD-adjacent approach; Task 1 = GREEN (implementation), Task 2 = RED+GREEN (tests written and passing)_

## Files Created/Modified

- `backend/services/patient_store.py` — Public `promote_to_patient_tables()` + 4 `_promote_*` functions + `_load_aliases`, `_normalize_analyte`, `_parse_br_date` helpers (314 lines)
- `backend/tests/patient/__init__.py` — Package marker (empty)
- `backend/tests/patient/test_patient_store.py` — 12 unit tests using MagicMock Supabase client, patch-based (256 lines)

## Decisions Made

- Observation pre-check uses SELECT then conditional INSERT (not upsert) because D-01 requires BOTH conflicting rows to coexist — upsert would overwrite the original value, losing history
- `_load_aliases` wrapped in try/except returning `{}` so promotion still works in dev environments without the `analyte_aliases` table applied; alias lookup failure degrades gracefully to raw-name normalization
- Brazilian date parsing falls back to `upload_date` (not `None`) to ensure a concrete `observed_date` for the dedup key — SQL `NULL != NULL` would create duplicate rows on every re-upload of the same document

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None — all imports resolved, all 12 tests passed on first run. Full 48-test suite green.

## User Setup Required

None - no external service configuration required. The Supabase migration (applied in Plan 01) must have been run before `promote_to_patient_tables()` is called in production, but no new setup is needed for this plan.

## Next Phase Readiness

- `promote_to_patient_tables()` is ready to be wired into `backend/api/upload.py` after `store_save()` (Plan 02-03)
- All 4 document families handled; unknown family silently skipped
- Soft-fail contract verified: upload pipeline will never fail due to promotion errors
- `analyte_aliases` lookup is live-table-backed; seeded data from 02-01 will be used in production

---
*Phase: 02-longitudinal-patient-data-model*
*Completed: 2026-04-06*
