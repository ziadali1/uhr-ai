---
phase: 02-longitudinal-patient-data-model
verified: 2026-04-05T13:30:00Z
status: human_needed
score: 7/8 must-haves verified
human_verification:
  - test: "Apply supabase/migrations/20260405000000_patient_tables.sql to live Supabase instance and confirm 6 tables exist"
    expected: "6 tables visible in Table Editor: patient_observations, patient_conditions, patient_medications, patient_allergies, patient_imaging_findings, analyte_aliases; SELECT count(*) FROM analyte_aliases returns 25"
    why_human: "Cannot connect to Supabase from CI — migration application requires a live DB session"
  - test: "Upload a lab PDF through the running application"
    expected: "Rows created in patient_observations with correct normalized_analyte, value_str, unit, observed_date"
    why_human: "End-to-end pipeline requires live Supabase + Azure services; cannot exercise in unit tests"
  - test: "Upload a clinical note PDF through the running application"
    expected: "Rows created in patient_conditions (clinical_status='active') and patient_medications"
    why_human: "Same as above — requires live services"
  - test: "Re-upload the same lab PDF"
    expected: "No new rows created in patient_observations for identical analyte/date/value (no-op confirmed)"
    why_human: "Dedup behavior verified in unit tests but live-DB idempotency requires manual confirmation"
---

# Phase 2: Longitudinal Patient Data Model — Verification Report

**Phase Goal:** Promote structured extraction output from per-document JSONB blobs into first-class queryable patient tables.
**Verified:** 2026-04-05T13:30:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | 6 Postgres tables defined: patient_observations, patient_conditions, patient_medications, patient_allergies, patient_imaging_findings, analyte_aliases | VERIFIED | `supabase/migrations/20260405000000_patient_tables.sql` contains 6 `CREATE TABLE IF NOT EXISTS` statements (grep count = 6) |
| 2 | analyte_aliases pre-seeded with 20+ common Brazilian lab terms | VERIFIED | SQL seed INSERT contains 25 rows (accented + unaccented variants); `ON CONFLICT (raw_name) DO NOTHING` present |
| 3 | Pydantic models exist for all 5 patient entity types | VERIFIED | `backend/models/patient.py` exports PatientObservation, PatientCondition, PatientMedication, PatientAllergy, PatientImagingFinding; `python -c "from models.patient import ..."` exits 0 |
| 4 | promote_to_patient_tables() dispatches to correct function per document_family | VERIFIED | `patient_store.py` lines 53-60: if/elif chain maps structured_lab, clinical_narrative, medication_document, imaging_narrative to respective `_promote_*` functions; unknown family silent skip |
| 5 | Duplicate lab values for same analyte/date with same value/unit are no-ops | VERIFIED | `_promote_observation` SELECT pre-check (lines 132-145): identical value_str+unit → early return; test_duplicate_observation_identical_is_noop PASSES |
| 6 | Conflicting lab values for same analyte/date set needs_review=True on newer row | VERIFIED | `_promote_observation` lines 143-147: different value_str or unit → `needs_review = True`; test_duplicate_observation_conflict_sets_needs_review PASSES |
| 7 | Upload of a lab/clinical document triggers promotion after store_save | VERIFIED | `backend/api/upload.py` lines 119-131: step 7 calls promote_to_patient_tables after store_save; import verified; `python -c "from api.upload import router"` exits 0 |
| 8 | All 5 tables populated from live document uploads | HUMAN NEEDED | Code path wired correctly; live-DB verification required (migration not confirmed applied; human-verify checkpoint in Plan 03 was auto-approved without documented evidence) |

**Score:** 7/8 truths verified

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `supabase/migrations/20260405000000_patient_tables.sql` | DDL for 6 tables + seed data | VERIFIED | 115 lines; 6 tables; 25 seed rows; non-unique index idx_obs_dedup on patient_observations; UNIQUE constraints on patient_conditions, patient_medications, patient_allergies |
| `backend/models/patient.py` | 5 Pydantic models | VERIFIED | 59 lines; 5 classes; all inherit BaseModel; no id/created_at fields; needs_review bool and observed_date str present in PatientObservation; Literal enums correct |
| `backend/services/patient_store.py` | Promotion dispatch + per-family functions + alias lookup | VERIFIED | 314 lines (exceeds 80-line minimum); exports promote_to_patient_tables; contains _load_aliases, _normalize_analyte, _parse_br_date, _promote_observation, _promote_lab, _promote_clinical, _promote_medications, _promote_imaging |
| `backend/tests/patient/__init__.py` | Package marker | VERIFIED | Exists (empty) |
| `backend/tests/patient/test_patient_store.py` | Unit tests for all promotion paths | VERIFIED | 256 lines (exceeds 60-line minimum); 12 test functions; all 12 pass |
| `backend/api/upload.py` | Step 7 promotion call after store_save | VERIFIED | Contains `from services.patient_store import promote_to_patient_tables` (line 18); step 7 block at lines 119-131; appears after store_save call at line 106 |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `backend/api/upload.py` | `backend/services/patient_store.py` | import + call after store_save | WIRED | Line 18: `from services.patient_store import promote_to_patient_tables`; line 121: call site inside try block after store_save at line 106 |
| `backend/services/patient_store.py` | `backend/services/supabase_store.py` | _get_client() reuse | WIRED | Line 27: `from services.supabase_store import _get_client`; used at line 49 |
| `backend/services/patient_store.py` | `backend/models/document.py` | re-parsing structured_data into typed models | WIRED | Lines 18-26 import StructuredResult, StructuredLab, ClinicalNote, MedicationDocument, ImagingReport, LabFinding, MedicationEntry; lines 54-60 show `StructuredLab(**data)` etc. |
| `backend/tests/patient/test_patient_store.py` | `backend/services/patient_store.py` | import and mock-based testing | WIRED | Line 26: `from services.patient_store import promote_to_patient_tables, _normalize_analyte, _parse_br_date` |
| `backend/models/patient.py` | `supabase/migrations/20260405000000_patient_tables.sql` | field names match column names | VERIFIED | normalized_analyte, raw_analyte, observed_date, needs_review, raw_condition, normalized_condition, clinical_status, verification_status all match between models and SQL |

---

## Data-Flow Trace (Level 4)

`patient_store.py` is a service (not a rendering component) — it writes to the DB rather than rendering data. Level 4 traces apply to data-producing services:

| Function | Data Source | DB Write Target | Produces Real Data | Status |
|----------|-------------|-----------------|-------------------|--------|
| `_promote_lab` | `StructuredLab(**data)` from `structured_result.structured_data` | `patient_observations` via insert | YES — loops `lab.findings`, calls `_promote_observation` per finding with actual row dict | FLOWING |
| `_promote_clinical` | `ClinicalNote(**data)` | `patient_conditions`, `patient_allergies`, `patient_medications` via upsert | YES — iterates diagnoses, suspected_diagnoses, allergies, medications lists | FLOWING |
| `_promote_medications` | `MedicationDocument(**data)` | `patient_medications` via upsert with dose/route/frequency | YES — iterates med_doc.medications entries | FLOWING |
| `_promote_imaging` | `ImagingReport(**data)` | `patient_imaging_findings` via insert | YES — single insert with modality, body_region, impression, urgency | FLOWING |
| `_load_aliases` | `analyte_aliases` table | N/A (read-only) | YES — live table query; returns {} on failure (safe degradation) | FLOWING |

---

## Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| patient_store module importable | `python -c "from services.patient_store import promote_to_patient_tables; print('OK')"` | OK | PASS |
| models.patient importable | `python -c "from models.patient import PatientObservation, PatientCondition, PatientMedication, PatientAllergy, PatientImagingFinding; print('OK')"` | OK | PASS |
| api.upload importable | `python -c "from api.upload import router; print('OK')"` | OK | PASS |
| 12 patient_store unit tests pass | `python -m pytest tests/patient/test_patient_store.py -v` | 12 passed in 0.53s | PASS |
| Full 48-test suite passes (no regression) | `python -m pytest tests/ -v` | 48 passed in 0.67s | PASS |
| promote_to_patient_tables appears after store_save in upload.py | line order check | store_save at line 106; promote_to_patient_tables at line 121 | PASS |
| on_conflict values use no spaces | grep on_conflict patient_store.py | "user_id,normalized_condition", "user_id,normalized_allergen", "user_id,normalized_medication" — no spaces | PASS |
| Migration SQL count | grep -c "CREATE TABLE IF NOT EXISTS" | 6 | PASS |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| STORE-01 | 02-01-PLAN.md | 5 queryable Postgres tables for longitudinal patient data | SATISFIED | 5 patient tables + analyte_aliases in migration SQL; Pydantic models match columns |
| STORE-02 | 02-02-PLAN.md, 02-03-PLAN.md | System promotes structured extraction results after every document upload | SATISFIED | upload.py step 7 calls promote_to_patient_tables after store_save; all 4 document families handled; soft-fail verified |
| STORE-03 | 02-02-PLAN.md | System deduplicates patient entities using tiered strategy (LOINC → alias table → fuzzy → flag for review) | PARTIAL — see note | Alias table + needs_review flag implemented; LOINC codes and fuzzy matching explicitly deferred to v2 per D-12 and D-16 in 02-CONTEXT.md; REQUIREMENTS.md marks as complete but full tiered strategy not implemented |

**Note on STORE-03:** The REQUIREMENTS.md description includes "LOINC → alias table → fuzzy → flag for review" as the full tiered strategy, but the CONTEXT.md decisions (D-12, D-16) explicitly scope v1 to alias table + flag-for-review only, with no LOINC or fuzzy matching. This is a deliberate scoping decision documented at the planning stage. The implemented dedup (alias lookup → lowercase fallback → needs_review flag on conflict) satisfies the core deduplication intent for Phase 2. LOINC and fuzzy are confirmed deferred to future phases. This is flagged as a known scope delta, not a missing implementation.

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `backend/services/patient_store.py` | 79 | `return {}` | INFO | Legitimate — inside `_load_aliases` except block; returns empty dict when analyte_aliases table doesn't exist yet (expected dev degradation path) |
| `backend/services/patient_store.py` | 106, 110 | `pass` | INFO | Legitimate — inside `_parse_br_date` except blocks for try-next-format logic |
| `backend/api/upload.py` | 128-130 | `import logging` inside except block | INFO | Minor style issue — logging module imported inside the except handler instead of at top of file; functional but unconventional |

No blockers or warnings found. No TODO/FIXME/PLACEHOLDER comments. No empty return statements in paths that render or produce patient data.

---

## Human Verification Required

### 1. Migration Applied to Supabase

**Test:** Open Supabase Dashboard → SQL Editor → paste contents of `supabase/migrations/20260405000000_patient_tables.sql` → Run.
**Expected:** 6 new tables appear in Table Editor; `SELECT count(*) FROM analyte_aliases` returns 25.
**Why human:** Requires live Supabase credentials and DB session. Cannot be verified programmatically without DB access.

### 2. Lab PDF Upload Creates patient_observations Rows

**Test:** Upload a lab report PDF through the application UI or API.
**Expected:** Rows created in `patient_observations` with `normalized_analyte` (canonical form if alias matches), `value_str`, `unit`, `observed_date` (ISO format), `needs_review=false`.
**Why human:** Requires running application with live Azure Document Intelligence + Supabase.

### 3. Clinical Note Upload Creates patient_conditions and patient_medications Rows

**Test:** Upload a clinical note PDF.
**Expected:** Rows in `patient_conditions` (clinical_status='active' for diagnoses, 'suspected' for suspected_diagnoses) and `patient_medications`. Row in `patient_allergies` if allergies extracted.
**Why human:** Same as above — requires live services.

### 4. Duplicate Upload is a No-Op in Live DB

**Test:** Upload the same lab PDF twice.
**Expected:** Second upload creates no new rows in `patient_observations` for analyte/date/value combinations already present. (Dedup tested in unit tests with mock client; this confirms the SQL constraint + application logic work together correctly.)
**Why human:** Unit tests mock the Supabase client; live-DB idempotency requires actual DB constraint interaction.

---

## Gaps Summary

No automated gaps found. All code artifacts exist, are substantive (no stubs), and are correctly wired. The 12 unit tests pass and no regression was introduced in the existing 36-test suite. All 5 pipeline links verified.

The single human_needed item is the live-database confirmation that the migration has been applied and that end-to-end uploads actually populate the patient tables. This was supposed to be verified in Plan 03 Task 2 (human-verify checkpoint), but the summary records it as "auto-approved" without documented evidence of tables being populated. The code is correct; the live confirmation is the outstanding item.

**STORE-03 scope note:** The requirement as written in REQUIREMENTS.md describes a 4-tier strategy (LOINC → alias → fuzzy → flag). Only tiers 2 and 4 are implemented. This is documented as intentional (D-12, D-16) but the requirement description overstates what Phase 2 delivers. Recommend updating REQUIREMENTS.md to reflect the v1 scope ("alias table + flag for review") and deferring LOINC/fuzzy to a future STORE-06 requirement, to avoid misleading downstream readers.

---

_Verified: 2026-04-05T13:30:00Z_
_Verifier: Claude (gsd-verifier)_
