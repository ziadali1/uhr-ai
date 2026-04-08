---
phase: 06-patient-timeline-api-and-dashboard
plan: 02
subsystem: api
tags: [python, fastapi, pydantic, supabase, patient-data, testing, pytest]

# Dependency graph
requires:
  - phase: 06-01
    provides: backend/services/patient_query.py with get_observations_timeline, get_patient_summary, get_conditions, get_medications
provides:
  - backend/api/timeline.py: FastAPI router with 3 endpoints (observations/{analyte}, conditions, medications)
  - backend/api/summary.py: FastAPI router with /patient/summary endpoint
  - backend/main.py: router registration, version 0.6.0, phase 6
  - backend/services/emergency.py: refactored to query patient tables with soft-fail
affects:
  - 06-03: frontend dashboard consumes /timeline and /patient/summary endpoints

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Pydantic response models per endpoint (ObservationTimelineItem, PatientSummaryResponse, etc.)
    - 404 HTTPException when get_patient_summary returns None
    - Emergency service soft-fail: _get_client exception -> empty lists, return EmergencyProfile not None
    - Blood type still extracted via regex on document text (D-10, no patient table column)

key-files:
  created:
    - backend/api/timeline.py
    - backend/api/summary.py
  modified:
    - backend/main.py
    - backend/services/emergency.py
    - backend/tests/timeline/test_emergency_refactor.py

key-decisions:
  - "Emergency soft-fail returns EmergencyProfile with empty lists when _get_client raises — never None on DB error"
  - "list_by_user for blood type is imported inline (lazy) inside try block to avoid circular import issues"
  - "ObservationTimelineItem.needs_review typed as bool (not bool | None) — matches Wave 0 stub requirement"
  - "test_soft_fail_on_table_error patches services.document_store.list_by_user (module-level) not services.emergency.list_by_user (lazy import inside try)"

patterns-established:
  - "Lazy import for document_store.list_by_user inside try block — isolation of blood type path"
  - "client_failed flag: distinguishes DB error from successful-but-empty query for None-return logic"

requirements-completed: [TIMELINE-01, TIMELINE-02]

# Metrics
duration: 5min
completed: 2026-04-08
---

# Phase 06 Plan 02: Timeline and Summary API Routers Summary

**FastAPI routers for 4 new endpoints, emergency service refactored to patient table queries with soft-fail, all 9 timeline tests passing**

## Performance

- **Duration:** 5 min
- **Completed:** 2026-04-08
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Created `backend/api/timeline.py` with 3 endpoints: `GET /timeline/observations/{analyte}`, `GET /timeline/conditions`, `GET /timeline/medications`
- Created `backend/api/summary.py` with `GET /patient/summary` endpoint; raises 404 when no data
- Defined Pydantic response models: `ObservationTimelineItem`, `ObservationTimelineResponse`, `PatientSummaryResponse`, `ConditionItem`, `MedicationItem`, `AllergyItem`, `LatestLabItem`
- Updated `backend/main.py`: registered both new routers, bumped version to `0.6.0`, phase to `6`
- Refactored `backend/services/emergency.py` to query `patient_conditions`, `patient_medications`, `patient_allergies` tables directly via `_get_client()` — replaced document entity scan
- Soft-fail: `_get_client` exceptions produce empty lists; `EmergencyProfile` always returned on DB error (not None)
- Blood type extraction remains on document text regex (D-10: no patient table column)
- `EmergencyProfile` return schema unchanged (D-11)
- Unskipped both `test_emergency_refactor.py` tests; all 9 timeline tests pass; full suite 97 passed, 5 skipped

## Task Commits

1. **Task 1: Create timeline and summary API routers + register in main.py** — `08a46b7`
2. **Task 2: Refactor emergency.py to query patient tables + unskip tests** — `8240d19`

## Files Created/Modified

- `backend/api/timeline.py` — Timeline router: 3 endpoints, 2 Pydantic models
- `backend/api/summary.py` — Summary router: 1 endpoint, 5 Pydantic models
- `backend/main.py` — Router registration, version 0.6.0 / phase 6
- `backend/services/emergency.py` — Patient table queries, soft-fail, blood type via docs
- `backend/tests/timeline/test_emergency_refactor.py` — 2 tests unskipped and passing

## Decisions Made

- Emergency soft-fail returns EmergencyProfile (not None) when `_get_client` raises — test spec required this
- `client_failed` flag distinguishes between "DB error (always return profile)" vs "DB success but empty (check docs, maybe None)"
- `list_by_user` imported lazily inside try block to avoid module-level circular import risk
- `test_soft_fail_on_table_error` patches `services.document_store.list_by_user` (the real module) since `list_by_user` is imported lazily at call time

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test soft-fail assertion mismatch with plan implementation**

- **Found during:** Task 2
- **Issue:** Wave 0 stub asserted `result is not None` for the soft-fail test, but the plan's implementation returned `None` when `_get_client` failed with no docs. These are contradictory.
- **Fix:** Introduced `client_failed` flag — when `_get_client` raises, always return `EmergencyProfile` with empty lists. The `None` return (no data) is only applicable when DB query succeeds but returns empty data AND no documents exist.
- **Files modified:** `backend/services/emergency.py`
- **Commit:** `8240d19`

**2. [Rule 2 - Missing mock] test_soft_fail_on_table_error lacked list_by_user mock**

- **Found during:** Task 2
- **Issue:** Wave 0 stub for `test_soft_fail_on_table_error` didn't mock `list_by_user`, meaning the test would attempt a real Supabase connection for blood type extraction.
- **Fix:** Added `patch("services.document_store.list_by_user", return_value=[])` to the test.
- **Files modified:** `backend/tests/timeline/test_emergency_refactor.py`
- **Commit:** `8240d19`

## Known Stubs

None — all endpoints return live data from patient tables.

## Self-Check: PASSED

- `backend/api/timeline.py`: FOUND
- `backend/api/summary.py`: FOUND
- `backend/main.py` contains `include_router(timeline_router`: FOUND
- `backend/main.py` contains `"version": "0.6.0"`: FOUND
- `backend/services/emergency.py` contains `client.table("patient_conditions")`: FOUND
- Commit `08a46b7`: FOUND
- Commit `8240d19`: FOUND
- All 9 timeline tests: PASSED
- Full suite 97 passed: PASSED

---
*Phase: 06-patient-timeline-api-and-dashboard*
*Completed: 2026-04-08*
