---
phase: 02-longitudinal-patient-data-model
plan: 01
subsystem: database
tags: [supabase, postgres, pydantic, migrations, patient-data]

# Dependency graph
requires:
  - phase: 01-adaptive-text-extraction
    provides: structured_result JSONB column written per document (patient_store.py will read this)
provides:
  - supabase/migrations/20260405000000_patient_tables.sql — DDL for 6 patient tables + 25 Brazilian analyte alias seed rows
  - backend/models/patient.py — 5 Pydantic models (PatientObservation, PatientCondition, PatientMedication, PatientAllergy, PatientImagingFinding) importable by patient_store.py
affects:
  - 02-02 (patient_store.py promotion service uses these models and tables)
  - 02-03 (integration tests depend on schema and models)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Supabase migration files in supabase/migrations/ (new directory, canonical home)
    - Non-unique index instead of UNIQUE constraint on patient_observations for application-level conflict detection (D-01)
    - Pydantic models with no id/created_at fields — those are Postgres-generated

key-files:
  created:
    - supabase/migrations/20260405000000_patient_tables.sql
    - backend/models/patient.py
  modified: []

key-decisions:
  - "patient_observations uses non-unique index idx_obs_dedup (not a UNIQUE constraint) to allow storing both conflicting rows per D-01; application code handles conflict detection"
  - "analyte_aliases seeded with 25 rows including both accented and unaccented Brazilian lab term variants for robust alias lookup"
  - "user_id stored as TEXT (not UUID) across all patient tables to match existing documents table pattern and avoid FK failures in mock/test environments"

patterns-established:
  - "Pattern: Supabase migration SQL lives in supabase/migrations/ with timestamp-prefixed filename"
  - "Pattern: Patient table Pydantic models omit id and created_at — Postgres auto-generates these"

requirements-completed: [STORE-01]

# Metrics
duration: 4min
completed: 2026-04-06
---

# Phase 02 Plan 01: Patient Tables Migration and Pydantic Models Summary

**Postgres DDL for 6 patient tables (observations, conditions, medications, allergies, imaging_findings, analyte_aliases) with 25 Brazilian lab alias seed rows and 5 matching Pydantic models**

## Performance

- **Duration:** 4 min
- **Started:** 2026-04-06T12:33:59Z
- **Completed:** 2026-04-06T12:37:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Created `supabase/migrations/20260405000000_patient_tables.sql` with 6 tables, correct constraint design per D-01 through D-17, and 25 Brazilian analyte alias rows
- Created `backend/models/patient.py` with 5 Pydantic BaseModel classes whose field names match migration SQL columns exactly
- All 5 models import successfully; Python verification passed

## Task Commits

Each task was committed atomically:

1. **Task 1: Create Supabase migration SQL with 6 tables and seed data** - `e4d0082` (feat)
2. **Task 2: Create Pydantic models for patient tables** - `184f438` (feat)

## Files Created/Modified

- `supabase/migrations/20260405000000_patient_tables.sql` - DDL for 6 patient tables + analyte_aliases seed data; ready to apply via Supabase Dashboard or CLI
- `backend/models/patient.py` - 5 Pydantic models for patient table rows; importable by patient_store.py (Plan 02)

## Decisions Made

- **patient_observations design (D-01):** Used non-unique index `idx_obs_dedup ON (user_id, normalized_analyte, observed_date)` instead of a UNIQUE constraint. D-01 requires storing both the existing and conflicting row (setting `needs_review=true` on the newer one), which is incompatible with a DB-level UNIQUE constraint that would reject the second insert. Application code in patient_store.py will handle conflict detection.
- **Seed rows (D-15):** Added both accented (`triglicerídeos`, `sódio`, `potássio`, `leucócitos`, `hemácias`) and unaccented (`triglicerideos`, `sodio`, `potassio`, `leucocitos`, `hemacias`) variants, resulting in 25 seed rows (plan specified 20+). This handles inconsistent diacritic use in extraction output.
- **user_id as TEXT:** Matches existing documents table pattern; avoids FK constraint failures when user_id is a mock string in dev/test.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

**Migration must be applied to Supabase before Phase 02 Plans 02-03 will work end-to-end.**

Apply via one of:
1. **Supabase Dashboard:** SQL Editor → paste contents of `supabase/migrations/20260405000000_patient_tables.sql` → Run
2. **Supabase CLI:** `supabase db push` (if CLI is installed and linked to project)

Tests in Plan 02-03 mock the Supabase client so they run without the live DB.

## Next Phase Readiness

- Migration SQL is ready to apply; once applied, the 6 tables exist in Supabase
- `backend/models/patient.py` is importable — Plan 02-02 (`patient_store.py`) can import `PatientObservation`, `PatientCondition`, `PatientMedication`, `PatientAllergy`, `PatientImagingFinding` immediately
- No blockers for Plan 02-02 execution

---
*Phase: 02-longitudinal-patient-data-model*
*Completed: 2026-04-06*
