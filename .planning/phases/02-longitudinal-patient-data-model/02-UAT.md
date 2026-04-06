---
status: complete
phase: 02-longitudinal-patient-data-model
source: [02-01-SUMMARY.md, 02-02-SUMMARY.md, 02-03-SUMMARY.md]
started: 2026-04-06T14:00:00Z
updated: 2026-04-06T14:05:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Cold Start Smoke Test
expected: Kill any running server/service. Clear ephemeral state (temp DBs, caches, lock files). Start the application from scratch. Server boots without errors, any seed/migration completes, and a primary query (health check, homepage load, or basic API call) returns live data.
result: issue
reported: "upload funciona. O site funciona. Mas dá o seguinte erro no terminal: GET /analysis HTTP/1.1 500 Internal Server Error — NotImplementedError: Análise via LLM será ativada com credenciais Azure configuradas."
severity: major
note: pre-existing stub in backend/services/analysis.py (committed before phase 2 in feat: Fase 3 commit); unrelated to phase 2 patient data model changes

### 2. Migration SQL File Exists and Is Complete
expected: `supabase/migrations/20260405000000_patient_tables.sql` exists and contains CREATE TABLE statements for all 6 tables: patient_observations, patient_conditions, patient_medications, patient_allergies, patient_imaging_findings, analyte_aliases — plus at least 20 seed rows for analyte_aliases.
result: pass

### 3. Pydantic Models Import Successfully
expected: Running `python -c "from backend.models.patient import PatientObservation, PatientCondition, PatientMedication, PatientAllergy, PatientImagingFinding; print('OK')"` from the project root prints `OK` with no errors.
result: pass

### 4. Full Unit Test Suite Passes (48 tests)
expected: Running the test suite (e.g., `pytest backend/tests/`) reports 48 tests collected and all pass — including the 12 new patient_store tests added in Plan 02-02. Zero failures or errors.
result: pass

### 5. Upload Pipeline Wires to Promotion (Code Inspection)
expected: Opening `backend/api/upload.py` shows `from services.patient_store import promote_to_patient_tables` at the top, and a step 7 block after `store_save()` that calls `promote_to_patient_tables(doc_id, user_id, structured_result, upload_date)` wrapped in a try/except.
result: pass

### 6. D-01 Conflict Detection: Conflicting Observation Gets needs_review=True
expected: The `test_patient_store.py` unit test for D-01 conflict detection passes: when a lab observation with the same analyte/date but a different value is re-promoted, the service inserts a second row with `needs_review=True` rather than overwriting the original. The original row remains unchanged.
result: pass

### 7. Soft-Fail: Promotion Error Never Breaks Upload
expected: The `test_patient_store.py` soft-fail test passes: when `promote_to_patient_tables()` raises an unexpected exception, it is caught internally and the function returns without re-raising. Confirmed by test: upload pipeline step 7 also wraps in try/except so an exception in promotion does not propagate to the caller.
result: pass

## Summary

total: 7
passed: 6
issues: 1
pending: 0
skipped: 0

## Gaps

- truth: "Server boots and all endpoints return live data with no unhandled errors"
  status: failed
  reason: "User reported: GET /analysis returns 500 — NotImplementedError raised in backend/services/analysis.py line 129 (intentional stub awaiting Azure credentials)"
  severity: major
  test: 1
  artifacts: [backend/services/analysis.py:129, backend/api/analysis.py:18]
  missing: []
  note: pre-existing — committed in Fase 3 before phase 2, not a phase 2 regression
