# Phase 6: Patient Timeline API and Dashboard — Context

**Gathered:** 2026-04-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Expose patient-level aggregates via new API endpoints and wire them into the frontend dashboard and emergency profile. This phase ships:

- `api/timeline.py` — `GET /timeline/observations/{analyte}`, `GET /timeline/conditions`, `GET /timeline/medications` endpoints
- `GET /patient/summary` — structured factual aggregate: active conditions, current medications, allergies, latest labs grouped by analyte
- Refactored `services/emergency.py` — queries patient tables instead of scanning document entities for medications, allergies, and conditions
- Updated `app/dashboard/page.tsx` and `components/dashboard/PatientSummary.tsx` — new structured patient data section added alongside the existing LLM analysis panel

This phase does NOT include: replacing the LLM analysis endpoint (`GET /analysis`), adding chart/visualization components (v2 requirement VIZ-01), modeling blood type in patient tables, clinical reasoning (Phase 7), security hardening (Phase 8).

</domain>

<decisions>
## Implementation Decisions

### Dashboard Update Strategy

- **D-01:** Do NOT replace the existing LLM analysis panel (`GET /analysis` / `PatientSummary.tsx`). Add structured patient data as a new section alongside the current view.
- **D-02:** The dashboard evolves incrementally: structured patient facts become the primary factual layer; LLM analysis remains as the interpretive/synthesis layer. Both coexist.
- **D-03:** The new structured section displays data from `GET /patient/summary` — active conditions, current medications, allergies, latest labs per analyte.

### Timeline API Response Shape

- **D-04:** `GET /timeline/observations/{analyte}` returns full observation records, not just date/value pairs. Each item includes:
  - `observed_at` — ISO date
  - `value_num` — numeric value if available
  - `value_str` — string representation
  - `unit`
  - `ref_low` — reference range lower bound
  - `ref_high` — reference range upper bound
  - `flag` — clinical flag (H/L/HH/LL or equivalent)
  - `document_id` — source document traceability
  - `analyte_raw` — original analyte name as extracted
  - `analyte_norm` — canonical/normalized analyte name
  - `needs_review` — dedup conflict flag from Phase 2 (include when available)
- **D-05:** Results are sorted by `observed_at` descending. Date range filter (`date_from`, `date_to`) is supported per TIMELINE-01.
- **D-06:** This response shape provides enough data for charts, clinical interpretation, and full traceability to source documents.

### Endpoint Coexistence

- **D-07:** Both `GET /patient/summary` and `GET /analysis` are maintained after this phase. They serve distinct purposes:
  - `/patient/summary` = structured factual patient aggregate (from patient tables, deterministic)
  - `/analysis` = LLM-generated interpretation and synthesis (from `analyze_patient()`)
- **D-08:** The new `PatientSummary` section in the dashboard calls `/patient/summary`. The existing LLM analysis section continues calling `/analysis` unchanged.

### Emergency Service Refactor

- **D-09:** Refactor `services/emergency.py` to query patient tables directly for medications, allergies, and active conditions — replacing the current scan of `list_by_user()` + `medical_entities` iteration.
- **D-10:** Blood type extraction stays on the current regex-based fallback approach. No `blood_type` column exists in patient tables — adding it is explicitly deferred to a later requirement.
- **D-11:** `EmergencyProfile` schema is not expanded in this phase. The refactor changes the data source only, not the output shape.
- **D-12:** Emergency service soft-fail pattern from Phase 2 (D-04) applies: patient table query failures must not break the emergency endpoint.

### Claude's Discretion

- Exact Pydantic response model field names for `/patient/summary` and `/timeline/observations/{analyte}`
- Whether timeline endpoints use query params or path params for date range filters
- How to handle `needs_review=True` observations in the summary view (e.g., show with a warning indicator, or include without flagging)
- Frontend component structure for the new structured data section (separate component vs. extending PatientSummary.tsx)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Patient tables (data source for all new endpoints)
- `backend/services/patient_store.py` — Promotion logic; shows patient table schemas and field names (patient_observations, patient_conditions, patient_medications, patient_allergies, patient_imaging_findings)
- `.planning/phases/02-longitudinal-patient-data-model/02-CONTEXT.md` — Phase 2 decisions: dedup strategy, conflict detection, needs_review flag, analyte_aliases

### Emergency service (being refactored)
- `backend/services/emergency.py` — Current document-scan implementation to be replaced with patient table queries
- `backend/api/emergency.py` — Emergency endpoints; EmergencyProfile schema used here must not change shape
- `backend/models/emergency.py` — EmergencyProfile, Allergy, Medication models

### Existing analysis endpoint (preserved, not modified)
- `backend/api/analysis.py` — GET /analysis endpoint; coexists with new /patient/summary
- `backend/services/analysis.py` — LLM-based analyze_patient(); do NOT modify in this phase

### Frontend dashboard (being extended)
- `frontend/app/dashboard/page.tsx` — Current dashboard page; new section added here
- `frontend/components/dashboard/PatientSummary.tsx` — Current LLM analysis display component; preserved, new structured component added alongside
- `frontend/lib/api.ts` — API client; new functions for /patient/summary and /timeline/* added here

### Phase 5 context (SQL result formatting patterns)
- `.planning/phases/05-query-routing-and-context-assembly/05-CONTEXT.md` — D-12/D-13: patient SQL results as ground truth, compact fact table formatting

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/services/supabase_store._get_client()` — Supabase client factory used throughout; timeline and summary services use the same pattern
- `backend/services/patient_store.py` — Shows exact field names in patient tables; timeline query functions can be added here or in a new `patient_query.py`
- `frontend/components/dashboard/PatientSummary.tsx` — Existing Section component (icon, title, color, children) is reusable for the new structured data section

### Established Patterns
- All backend services use `_get_client()` + try/except soft-fail for Supabase queries
- API routers use `Depends(get_current_user)` for auth; timeline and summary endpoints must follow this pattern
- Frontend API calls use `frontend/lib/api.ts` typed functions (see `getAnalysis()` as model)

### Integration Points
- `backend/main.py` — New `timeline` and `summary` routers must be registered here
- `frontend/app/dashboard/page.tsx` — New structured data section renders alongside existing `<PatientSummary />` LLM section
- `backend/services/emergency.py` — Refactor: replace `list_by_user()` call with direct patient table queries; blood type extraction stays unchanged

</code_context>

<specifics>
## Specific Ideas

- The structured patient data section on the dashboard is additive — it appears alongside (not replacing) the existing Análise do Histórico section
- Response shape for `/timeline/observations/{analyte}` is deliberately rich (D-04) to enable future chart rendering without an API change
- Blood type is intentionally left out of the patient tables refactor — no scope creep on the schema

</specifics>

<deferred>
## Deferred Ideas

- Blood type as a structured patient-level field (dedicated column or patient_demographics table) — deferred to a later requirement
- Lab trend chart visualization (line chart for analyte over time) — v2 requirement VIZ-01, explicitly deferred
- Retiring `GET /analysis` in favor of `/patient/summary` — future phase decision once structured data proves sufficient

</deferred>

---

*Phase: 06-patient-timeline-api-and-dashboard*
*Context gathered: 2026-04-08*
