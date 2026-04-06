# Phase 2: Longitudinal Patient Data Model - Context

**Gathered:** 2026-04-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Promote structured extraction output (already in `documents.structured_result` JSONB) into 5 first-class queryable Postgres tables: `patient_observations`, `patient_conditions`, `patient_medications`, `patient_allergies`, `patient_imaging_findings`. Also create `analyte_aliases` lookup table. Wire a promotion step into the upload pipeline (after RAG indexing) that is additive, soft-fail, idempotent, and retryable.

This phase delivers the patient data layer. It does NOT include retrieval improvements, frontend timeline views, migration of existing `health_entries`, or backfill of existing documents — those are Phases 3–6.

</domain>

<decisions>
## Implementation Decisions

### Deduplication Strategy

- **D-01:** For `patient_observations` (labs): deduplicate using `user_id + normalized_analyte + observed_date`. If all three match and values/units are identical → upsert. If values or units conflict for the same analyte/date → store both rows and set `needs_review = true` on the newer one. Do NOT merge conflicting values automatically.
- **D-02:** For `patient_conditions`, `patient_medications`, `patient_allergies`: use upsert semantics on canonical name. Latest document wins — updates the existing entry. No conflict-flagging needed for these families.
- **D-03:** Dedup key for observations: `(user_id, normalized_analyte, observed_date)` as a composite unique constraint. Normalized analyte comes from `analyte_aliases` lookup; falls back to lowercased raw name if no alias found.

### Promotion Failure Behavior

- **D-04:** Soft-fail. Promotion failure must never block document upload. Document and `structured_result` persist normally regardless of patient table promotion outcome.
- **D-05:** On failure: log `document_id` + error details. Do not raise HTTP exception.
- **D-06:** Promotion function must be idempotent — calling it multiple times with the same document produces the same result (safe to retry). Use `ON CONFLICT DO UPDATE` or equivalent upsert patterns, never blind inserts.
- **D-07:** Follow the `text_extraction_meta` pattern from Phase 1 (`supabase_store.py` lines 42–47): wrap promotion in try/except, log silently, continue.

### Conditions & Medications Schema

- **D-08:** Store both raw and normalized values. Raw = string as extracted from ClinicalNote/MedicationDocument. Normalized = canonical form when resolvable via alias table or simple string normalization.
- **D-09:** `patient_conditions` key fields: `raw_condition` (str), `normalized_condition` (str | null), `clinical_status` (active | resolved | suspected | null), `verification_status` (confirmed | provisional | null), `source_document_id` (FK to documents).
- **D-10:** `patient_medications` key fields: `raw_medication` (str), `normalized_medication` (str | null), `dose` (str | null), `route` (str | null), `frequency` (str | null), `status` (active | stopped | null), `source_document_id`.
- **D-11:** `patient_allergies` key fields: `raw_allergen` (str), `normalized_allergen` (str | null), `reaction` (str | null), `source_document_id`.
- **D-12:** No full ontology (ICD, SNOMED, RxNorm) mapping in v1. Normalization is string-level only (canonical name via alias table or lowercase+strip).
- **D-13:** `patient_imaging_findings` key fields: `modality` (str | null), `body_region` (str | null), `impression` (str | null), `urgency` (routine | urgent | critical | null), `source_document_id`.

### analyte_aliases Table

- **D-14:** Use a Supabase table (`analyte_aliases`), NOT a hardcoded dict. Schema: `id`, `raw_name` (str, unique), `canonical_name` (str), `unit_canonical` (str | null).
- **D-15:** Pre-seed with common Brazilian lab terms: Hb, Hemoglobina, HbA1c, hemoglobina glicada, glicose, glicemia, creatinina, ureia, colesterol total, LDL, HDL, triglicerídeos, TSH, T4 livre, sódio, potássio, PCR, plaquetas, leucócitos, hemácias. Exact seed list determined by planner/executor — user approves this scope.
- **D-16:** No LOINC codes in v1. Table grows over time as new terms are encountered.
- **D-17:** Lookup is case-insensitive. If raw_name not found in alias table → normalized_analyte = raw name lowercased and stripped.

### Claude's Discretion

- Exact Pydantic model names and field ordering for the 5 new patient table models
- Supabase migration file structure and naming (follow existing conventions in codebase if any)
- Whether `patient_store.py` is a single file or split by domain (one function per family is acceptable)
- Internal promotion function signatures
- Exact logging format for soft-fail errors

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing Supabase patterns
- `backend/services/supabase_store.py` — Existing Supabase client pattern, how rows are inserted, _row_to_detail pattern
- `backend/services/health_store.py` — Manual health entry persistence; schema for existing `health_entries` table

### Existing data models
- `backend/models/document.py` — StructuredResult, StructuredLab, LabFinding, ImagingReport, ClinicalNote, MedicationDocument, MedicationEntry — these are the SOURCE models that promotion reads from

### Upload pipeline integration point
- `backend/api/upload.py` — Where step 7 (promotion) will be added; existing pipeline steps 1–6 visible here

### Requirements for this phase
- `.planning/REQUIREMENTS.md` §Patient Data Model — STORE-01, STORE-02, STORE-03 definitions
- `.planning/ROADMAP.md` §Phase 2 — Done-when criteria and plan breakdown

### Phase 1 context (patterns to continue)
- `.planning/phases/01-adaptive-text-extraction/01-05-edge-cases-PLAN.md` — Example of how Phase 1 did try/except soft-fail on Supabase column inserts (D-07 pattern)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `supabase_store.py` → `_get_client()` pattern: copy this singleton client initialization into `patient_store.py`
- `models/document.py` → `StructuredLab`, `ImagingReport`, `ClinicalNote`, `MedicationDocument` are the exact source models to read during promotion
- `models/document.py` → `LabFinding` already has: name, value, unit, reference_range, flag fields — maps directly to `patient_observations`

### Established Patterns
- Pydantic 2.x models in `models/` for all schemas (no logic)
- Supabase client as module-level singleton (`_client: Client | None = None`)
- try/except around new Supabase columns (Phase 1 precedent for table-not-yet-migrated)
- Router pattern: thin `api/` handler delegates to `services/` function

### Integration Points
- `backend/api/upload.py` line 116: after `store_save(...)`, add `promote_to_patient_tables(doc_id, user_id, result.structured_result)` wrapped in try/except
- New `backend/services/patient_store.py` — promotion functions per family
- New Supabase migration for 6 tables (5 patient tables + analyte_aliases)

</code_context>

<specifics>
## Specific Ideas

- **Idempotency via upsert**: all inserts should use `ON CONFLICT DO UPDATE` semantics so re-running promotion on the same document is safe
- **needs_review flag**: only on `patient_observations` for conflicting lab values; simple boolean column
- **Seed list scope**: ~20 common Brazilian lab analytes (see D-15) — enough to handle most real documents without over-engineering
- **No LOINC in v1**: explicitly out of scope per user decision

</specifics>

<deferred>
## Deferred Ideas

- Full LOINC / SNOMED / RxNorm ontology mapping — future milestone
- Review UI for `needs_review` flagged observations — future phase
- Migration of existing `health_entries` into new patient tables — Phase 3
- Backfill of existing documents' structured_result — Phase 3
- Cross-document entity linking (same lab across documents) — noted in PROJECT.md active requirements, addressed in retrieval phases

</deferred>

---

*Phase: 02-longitudinal-patient-data-model*
*Context gathered: 2026-04-05*
