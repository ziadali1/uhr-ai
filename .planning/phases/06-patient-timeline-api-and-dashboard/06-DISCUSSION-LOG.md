# Phase 6: Patient Timeline API and Dashboard — Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-08
**Phase:** 06-patient-timeline-api-and-dashboard
**Areas discussed:** Dashboard update scope, Timeline API response shape, Patient summary vs. analysis endpoint, Emergency service refactor scope

---

## Dashboard Update Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Replace LLM analysis with structured data | Retire GET /analysis; PatientSummary shows patient table data only | |
| Add structured data alongside LLM analysis | New section added; both panels coexist | ✓ |
| Keep existing dashboard, add separate page | No dashboard changes; timeline exposed via separate route only | |

**User's choice:** Add structured patient data as a new section alongside the current LLM analysis panel. Structured facts = primary factual layer; LLM analysis = interpretive/synthesis layer. Both coexist.

**Notes:** Dashboard evolves incrementally. No retirement of /analysis in this phase.

---

## Timeline API Response Shape

| Option | Description | Selected |
|--------|-------------|----------|
| Minimal (date + value + unit) | Lightweight; enough for simple display | |
| Full observation record | All patient_observations fields including ref range, flag, document_id, needs_review | ✓ |
| Aggregated summary | Pre-computed stats (min, max, avg) per analyte with trend | |

**User's choice:** Full observation record per item: `observed_at`, `value_num`, `value_str`, `unit`, `ref_low`, `ref_high`, `flag`, `document_id`, `analyte_raw`, `analyte_norm`, `needs_review`. Sorted by `observed_at` descending. Date range filter supported.

**Notes:** Rich response shape chosen to enable future chart rendering (VIZ-01) without requiring an API change.

---

## Patient Summary vs. Analysis Endpoint

| Option | Description | Selected |
|--------|-------------|----------|
| /patient/summary replaces /analysis | One endpoint, structured + interpreted | |
| Both endpoints coexist, different purposes | /patient/summary = structured facts; /analysis = LLM synthesis | ✓ |
| Merge into single endpoint with mode param | ?mode=structured or ?mode=analysis | |

**User's choice:** Keep both endpoints with distinct purposes. `/patient/summary` = deterministic structured aggregate from patient tables. `/analysis` = LLM-generated interpretation. They serve different consumers and should coexist.

---

## Emergency Service Refactor Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Full refactor including blood type | Add blood_type to patient tables, query everything from tables | |
| Partial refactor: medications/allergies/conditions from tables, blood type stays regex | Change data source only for structured entities; keep existing blood type logic | ✓ |
| Defer entire refactor | Keep emergency.py scanning documents | |

**User's choice:** Refactor medications, allergies, and conditions to query patient tables directly. Blood type stays on the regex fallback (no patient table for it yet). EmergencyProfile schema unchanged — output shape stays the same.

**Notes:** Blood type as a structured patient field is explicitly deferred. No schema expansion in this phase.

---

## Claude's Discretion

- Exact Pydantic field names for /patient/summary and /timeline/observations/{analyte} response models
- Whether date range filters use query params or path params
- How needs_review observations are surfaced in the dashboard (warning indicator or silent inclusion)
- Frontend component structure for new structured data section

## Deferred Ideas

- Blood type patient table / patient_demographics schema
- Lab trend chart (VIZ-01) — v2 requirement
- Retiring /analysis once structured data proves sufficient
