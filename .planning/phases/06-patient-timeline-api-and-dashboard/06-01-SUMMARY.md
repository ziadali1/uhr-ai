---
phase: 06-patient-timeline-api-and-dashboard
plan: 01
subsystem: api
tags: [python, fastapi, supabase, patient-data, testing, pytest]

# Dependency graph
requires:
  - phase: 02-longitudinal-patient-data-model
    provides: patient_observations, patient_conditions, patient_medications, patient_allergies tables
  - phase: 03-migration-and-backfill
    provides: populated patient tables with migrated health_entries and backfilled structured_result
provides:
  - backend/services/patient_query.py: query service for timeline observations, patient summary, conditions, medications
  - backend/tests/timeline/: test package for Phase 6 validation
affects:
  - 06-02: timeline and summary API endpoints depend on patient_query.py
  - 06-03: frontend dashboard consumes the API built on top of patient_query.py

# Tech tracking
tech-stack:
  added: []
  patterns:
    - soft-fail with _log.warning on all public query functions
    - _enrich_observation() derives computed fields (value_num, ref_low, ref_high) from raw DB columns
    - deduplication by normalized_analyte with seen:set pattern for latest labs

key-files:
  created:
    - backend/services/patient_query.py
    - backend/tests/timeline/__init__.py
    - backend/tests/timeline/test_patient_query.py
    - backend/tests/timeline/test_emergency_refactor.py
  modified: []

key-decisions:
  - "value_num not stored in DB — derived at query time from value_str via float() cast"
  - "ref_low/ref_high not stored in DB — parsed from reference_range string at query time"
  - "Wave 0 stubs for emergency refactor remain skipped — emergency.py refactor is Plan 02 scope"
  - "date_from/date_to sliced to [:10] chars before Supabase .gte/.lte call per Pitfall 4"

patterns-established:
  - "soft-fail pattern: try/except in every public function, _log.warning, return None or []"
  - "Wave 0 stubs: placed imports inside test bodies to prevent ImportError during collection"
  - "_enrich_observation(): pure function mapping raw DB row to API response shape"

requirements-completed: [TIMELINE-01, TIMELINE-02]

# Metrics
duration: 2min
completed: 2026-04-08
---

# Phase 06 Plan 01: Patient Query Service Layer Summary

**Read-path Supabase query service with 4 public functions, enrichment helpers, and 7 passing unit tests — Phase 6 data access foundation**

## Performance

- **Duration:** 2 min
- **Started:** 2026-04-08T19:07:43Z
- **Completed:** 2026-04-08T19:09:55Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Created `backend/services/patient_query.py` with 4 public functions (get_observations_timeline, get_patient_summary, get_conditions, get_medications) and 5 private helpers
- Implemented observation enrichment: value_num derived from value_str via float() cast, ref_low/ref_high parsed from reference_range "low-high" string
- Latest-labs deduplication: _query_latest_labs keeps most recent row per normalized_analyte using seen:set
- All public functions soft-fail (log warning, return None/[]) — follows project D-04 pattern
- 9 Wave 0 stubs collected (7 for patient_query, 2 for emergency refactor); 7 unskipped and passing after implementation

## Task Commits

Each task was committed atomically:

1. **Task 1: Create Wave 0 test stubs** - `4e3ca31` (test)
2. **Task 2: Implement patient_query.py service layer** - `df203b2` (feat)

## Files Created/Modified

- `backend/services/patient_query.py` - Patient read-path query service with timeline, summary, conditions, medications
- `backend/tests/timeline/__init__.py` - Empty package marker for timeline tests
- `backend/tests/timeline/test_patient_query.py` - 7 unit tests (all passing)
- `backend/tests/timeline/test_emergency_refactor.py` - 2 Wave 0 stubs (skipped, for Plan 02)

## Decisions Made

- value_num is NOT a DB column — derived at query-time from value_str via float() cast (per plan interface spec)
- ref_low/ref_high are NOT DB columns — parsed from reference_range "low-high" string at query-time
- date_from/date_to sliced to [:10] chars before Supabase .gte/.lte call to handle full ISO timestamps
- Wave 0 stubs for emergency refactor remain skipped — emergency.py refactor deferred to Plan 02

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## Known Stubs

- `backend/tests/timeline/test_emergency_refactor.py` — 2 stubs remain skipped (`@pytest.mark.skip(reason="Wave 0 stub")`). These are intentional Wave 0 stubs for the emergency.py refactor, which is Plan 02 scope. Will be unskipped in Plan 02 task 2.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `patient_query.py` is ready for Plan 02 to import and use in `api/timeline.py` and `api/summary.py`
- Emergency refactor Wave 0 stubs are in place and will be unskipped in Plan 02
- Full test suite: 95 passed, 7 skipped — no regressions introduced

---
*Phase: 06-patient-timeline-api-and-dashboard*
*Completed: 2026-04-08*
