# Phase 6: Patient Timeline API and Dashboard — Research

**Researched:** 2026-04-08
**Domain:** FastAPI route layer, Supabase table queries, Next.js React components, Pydantic response models
**Confidence:** HIGH

## Summary

Phase 6 is purely a wiring phase — all five patient tables already exist and are populated (STORE-01 through STORE-05 complete). The work is: expose those tables through new FastAPI endpoints, refactor `emergency.py` to query tables instead of scanning documents, and add a new structured data panel to the dashboard that calls `GET /patient/summary`.

No new external dependencies are introduced. The backend pattern is already established: `_get_client()` + try/except soft-fail + `Depends(get_current_user)` on every authenticated endpoint. The frontend pattern is equally established: typed `api.ts` functions + `useEffect` + reuse of the existing `Section` component from `PatientSummary.tsx`.

The phase has two distinct risk areas: (1) the `patient_observations` table stores `value_str` (string) and optionally `value_num` is NOT a stored column — the D-04 response shape requests it, so the query must either cast or omit it; (2) the emergency refactor must preserve soft-fail behavior (D-12) and must not change `EmergencyProfile` shape (D-11).

**Primary recommendation:** Implement in three tracks — (a) backend timeline/summary service + API routers, (b) emergency.py refactor, (c) frontend `PatientStructuredData` component + `api.ts` additions. Each track is independently testable.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Do NOT replace the existing LLM analysis panel. Add structured patient data as a new section alongside.
- **D-02:** Dashboard evolves incrementally: structured patient facts become the primary factual layer; LLM analysis remains as the interpretive/synthesis layer. Both coexist.
- **D-03:** New structured section displays data from `GET /patient/summary` — active conditions, current medications, allergies, latest labs per analyte.
- **D-04:** `GET /timeline/observations/{analyte}` returns full observation records per item: `observed_at`, `value_num`, `value_str`, `unit`, `ref_low`, `ref_high`, `flag`, `document_id`, `analyte_raw`, `analyte_norm`, `needs_review`.
- **D-05:** Results sorted by `observed_at` descending. Date range filter (`date_from`, `date_to`) supported.
- **D-06:** Response shape is deliberately rich to enable future chart rendering without an API change.
- **D-07:** Both `GET /patient/summary` and `GET /analysis` are maintained. They serve distinct purposes.
- **D-08:** New `PatientSummary` section calls `/patient/summary`. Existing LLM analysis section continues calling `/analysis` unchanged.
- **D-09:** Refactor `services/emergency.py` to query patient tables directly for medications, allergies, active conditions.
- **D-10:** Blood type extraction stays on the current regex-based fallback. No `blood_type` column in patient tables.
- **D-11:** `EmergencyProfile` schema is NOT expanded. Refactor changes data source only, not output shape.
- **D-12:** Emergency service soft-fail pattern from Phase 2 (D-04) applies: patient table query failures must not break the emergency endpoint.

### Claude's Discretion

- Exact Pydantic response model field names for `/patient/summary` and `/timeline/observations/{analyte}`
- Whether timeline endpoints use query params or path params for date range filters
- How to handle `needs_review=True` observations in the summary view (e.g., show with a warning indicator, or include without flagging)
- Frontend component structure for the new structured data section (separate component vs. extending PatientSummary.tsx)

### Deferred Ideas (OUT OF SCOPE)

- Blood type as a structured patient-level field (dedicated column or patient_demographics table)
- Lab trend chart visualization (line chart for analyte over time) — v2 requirement VIZ-01
- Retiring `GET /analysis` in favor of `/patient/summary`
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| TIMELINE-01 | API exposes patient observation timeline (lab values by analyte over time, filterable by date range) | `patient_observations` table has `normalized_analyte`, `observed_date`, `value_str`, `flag`, `needs_review`; query with `.eq("normalized_analyte", analyte)` + optional `.gte/.lte` on `observed_date` |
| TIMELINE-02 | API exposes active conditions, current medications, and allergies as patient-level aggregates (not per-document) | `patient_conditions`, `patient_medications`, `patient_allergies` tables are already populated with upsert semantics; `GET /patient/summary` queries all three + latest obs per analyte |
| TIMELINE-03 | Frontend dashboard displays longitudinal lab trends and active clinical status | New `PatientStructuredData` component added below existing `<PatientSummary />` in `dashboard/page.tsx`; calls `/patient/summary`; renders 4 Section cards |
</phase_requirements>

---

## Standard Stack

### Core (all already in project — no new installs)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | existing | API routing for timeline/summary endpoints | Already used for all backend endpoints |
| Pydantic v2 | existing | Request/response models; use `model_dump()` not `.dict()` | All existing models use Pydantic v2 |
| supabase-py | existing | Supabase client for table queries | Used via `_get_client()` throughout |
| React + Next.js | existing | Frontend component for structured data panel | Existing dashboard is Next.js App Router |
| lucide-react | existing | Icons (FlaskConical for labs, Stethoscope, Pill, AlertTriangle) | Already imported in PatientSummary.tsx |

**No new packages to install.** Phase 6 is pure wiring on top of the existing stack.

---

## Architecture Patterns

### Established Backend Pattern (HIGH confidence — read directly from source)

Every authenticated endpoint follows this exact shape:

```python
# From backend/api/analysis.py — model for new routers
from fastapi import APIRouter, Depends, HTTPException
from utils.auth import get_current_user

router = APIRouter()

@router.get("/patient/summary", response_model=PatientSummaryResponse)
def get_patient_summary(user_id: str = Depends(get_current_user)):
    result = query_patient_summary(user_id)
    if result is None:
        raise HTTPException(status_code=404, detail="...")
    return result
```

### Established Service Pattern (HIGH confidence — read directly from patient_store.py)

```python
# Soft-fail Supabase query pattern — identical to promotion pattern
from services.supabase_store import _get_client

def query_patient_summary(user_id: str) -> dict | None:
    try:
        client = _get_client()
        # ... query logic ...
        return result
    except Exception as exc:
        _log.warning("patient_query failed user_id=%s: %s", user_id, exc)
        return None
```

### Supabase Query Patterns (HIGH confidence — verified in patient_store.py)

```python
# Filter by user + eq filter
rows = client.table("patient_conditions").select("*").eq("user_id", user_id).execute()

# Filter with optional date range (for TIMELINE-01)
query = client.table("patient_observations").select("*").eq("user_id", user_id).eq("normalized_analyte", analyte).order("observed_date", desc=True)
if date_from:
    query = query.gte("observed_date", date_from)
if date_to:
    query = query.lte("observed_date", date_to)
rows = query.execute()
```

### Router Registration Pattern (HIGH confidence — read from main.py)

```python
# In backend/main.py — add alongside existing routers
from api.timeline import router as timeline_router
from api.summary import router as summary_router

app.include_router(timeline_router, tags=["Timeline"])
app.include_router(summary_router, tags=["Paciente"])
```

### Frontend API Client Pattern (HIGH confidence — read from lib/api.ts)

```typescript
// Pattern: typed interface + authHeaders + fetch — from getAnalysis()
export interface PatientSummaryResponse { ... }

export async function getPatientSummary(): Promise<PatientSummaryResponse> {
  const res = await fetch(`${API_BASE}/patient/summary`, { headers: await authHeaders() });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Erro ao carregar dados clínicos");
  }
  return res.json();
}
```

### Frontend Component Pattern (HIGH confidence — read from PatientSummary.tsx)

The `Section` component in `PatientSummary.tsx` is already exported (lowercase `function Section`) — it is currently local to that file. The new `PatientStructuredData.tsx` needs it too.

**Resolution:** Create `PatientStructuredData.tsx` as a new `"use client"` component that duplicates the `Section` component locally (it's 14 lines) or re-export `Section` from `PatientSummary.tsx`. The simpler path is to duplicate — avoids breaking the existing component's internal structure.

### Recommended Project Structure for New Files

```
backend/
├── api/
│   ├── timeline.py          # GET /timeline/observations/{analyte}, /conditions, /medications
│   └── summary.py           # GET /patient/summary
├── services/
│   └── patient_query.py     # Query functions (separate from patient_store promotion logic)

frontend/
├── components/dashboard/
│   └── PatientStructuredData.tsx   # New "use client" component
├── lib/
│   └── api.ts               # Add getPatientSummary(), getTimeline*() functions
└── app/dashboard/
    └── page.tsx             # Add <PatientStructuredData /> below <PatientSummary />
```

### Anti-Patterns to Avoid

- **Modifying `services/analysis.py` or `api/analysis.py`:** D-08 is explicit — do NOT touch the LLM analysis endpoint in this phase.
- **Expanding `EmergencyProfile` schema:** D-11 prohibits this. The refactor in `emergency.py` changes query source only.
- **Raising exceptions from patient query functions:** All query functions must soft-fail (log + return None/empty), matching D-12 and Phase 2 D-04 pattern.
- **Using `.dict()` instead of `.model_dump()`:** Pydantic v2 uses `model_dump()`. See Phase 5 decision notes.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Auth token validation | Custom JWT parsing | `Depends(get_current_user)` from `utils/auth.py` | Already handles mock mode + real Supabase JWT |
| Supabase client factory | New client instantiation | `_get_client()` from `services/supabase_store.py` | Singleton pattern, already handles env vars |
| Date range filtering | Custom SQL | Supabase `.gte()` / `.lte()` chained on query | Already used throughout, supabase-py supports chaining |
| Icon components | Custom SVG | `lucide-react` (already installed) | `FlaskConical`, `Activity` already available |

---

## Critical Schema Facts (Verified from patient_store.py)

These are the exact column names in the patient tables. Queries and Pydantic models MUST use these names.

### `patient_observations` columns
| Column | Type | Notes |
|--------|------|-------|
| `id` | uuid | PK |
| `user_id` | text | matches documents table pattern |
| `document_id` | text | FK to documents |
| `normalized_analyte` | text | canonical name (from alias lookup) |
| `raw_analyte` | text | original extracted name |
| `value_str` | text | string representation |
| `unit` | text \| null | |
| `reference_range` | text \| null | raw string e.g. "3.5-5.0" |
| `flag` | text \| null | "normal", "high", "low", "borderline", "critical" (from LabFinding.flag) |
| `observed_date` | text | ISO YYYY-MM-DD |
| `needs_review` | bool | conflict flag from dedup |

**CRITICAL GAP:** `value_num` is NOT a column in `patient_observations`. Decision D-04 requires it in the timeline response. The endpoint must either: (a) attempt `float()` cast from `value_str` at query time in Python and include it in the Pydantic response, or (b) return `value_num: null` always. Option (a) is preferable for D-06 (chart-readiness). `ref_low`/`ref_high` also do not exist as columns — they must be parsed from `reference_range` string at query time if included, or omitted/nulled.

**RECOMMENDED:** Parse `value_num` from `value_str` in the service layer using `try: float(value_str)`. Parse `ref_low`/`ref_high` from `reference_range` using split on `-`. Both are best-effort: return `None` on parse failure.

### `patient_conditions` columns
| Column | Type | Notes |
|--------|------|-------|
| `raw_condition` | text | |
| `normalized_condition` | text | |
| `clinical_status` | text | "active", "suspected", "resolved" |
| `verification_status` | text | "confirmed", "provisional" |
| `document_id` | text | source document |

### `patient_medications` columns
| Column | Type | Notes |
|--------|------|-------|
| `raw_medication` | text | |
| `normalized_medication` | text | |
| `dose` | text \| null | |
| `route` | text \| null | |
| `frequency` | text \| null | |
| `status` | text | "active", "stopped" |

### `patient_allergies` columns
| Column | Type | Notes |
|--------|------|-------|
| `raw_allergen` | text | |
| `normalized_allergen` | text | |
| `reaction` | text \| null | |

---

## Common Pitfalls

### Pitfall 1: `value_num` and `ref_low`/`ref_high` are not stored columns
**What goes wrong:** Writing `client.table("patient_observations").select("value_num")` raises a Supabase/PostgREST error — column does not exist.
**Why it happens:** D-04 defines them in the response shape, but the table schema (visible in patient_store.py's INSERT dict) only stores `value_str` and `reference_range`.
**How to avoid:** Select `value_str` and `reference_range`, then derive `value_num` and `ref_low`/`ref_high` in the Python service layer.
**Warning signs:** PostgREST 400 error mentioning unknown column.

### Pitfall 2: `Section` component is not exported from PatientSummary.tsx
**What goes wrong:** `import { Section } from "@/components/dashboard/PatientSummary"` fails — `Section` is defined as a plain function, not exported.
**Why it happens:** The component was built as internal to `PatientSummary.tsx`.
**How to avoid:** Either add `export` to `Section` in `PatientSummary.tsx`, or copy the 14-line component into `PatientStructuredData.tsx`. Copying is safer (no risk of breaking existing component).

### Pitfall 3: Emergency refactor breaks soft-fail
**What goes wrong:** If the patient table query in `emergency.py` raises an unhandled exception, the entire `/emergency/{user_id}` endpoint returns 500 instead of degrading gracefully.
**Why it happens:** The original `list_by_user()` call is not wrapped in try/except — it either succeeds or propagates. The new patient table queries must be wrapped.
**How to avoid:** Wrap each patient table query (conditions, medications, allergies) in its own try/except. On failure, log and return empty list. D-12 explicitly requires this.

### Pitfall 4: `observed_date` column is text (not timestamp)
**What goes wrong:** Date range filtering with `.gte("observed_date", "2025-01-01")` works correctly for ISO YYYY-MM-DD strings (lexicographic sort = date sort). But if any row has a non-ISO date stored (bug from prior promotion), the filter silently misses it.
**Why it happens:** `_parse_br_date` can return `fallback` which is `upload_date` (also a string but possibly ISO datetime, not just date).
**How to avoid:** Slice date strings to 10 chars in query params. Accept this as a known limitation.

### Pitfall 5: `GET /timeline/conditions` and `GET /timeline/medications` overlap with `GET /patient/summary`
**What goes wrong:** Confusion about what each endpoint returns. Risk of redundant implementation or planners designing overlapping endpoints.
**Why it happens:** CONTEXT.md D-07 defines `/patient/summary` as the aggregate view. The timeline endpoints for conditions/medications are useful for future traceability (per-document history) but are not required for the dashboard.
**How to avoid:** `/patient/summary` = latest/current state of all categories. `/timeline/conditions` = full history with document_id and timestamps. They are complementary, not redundant.

### Pitfall 6: Router not registered in main.py
**What goes wrong:** New endpoints return 404 even though the router file is correct.
**Why it happens:** FastAPI requires explicit `app.include_router()` calls.
**How to avoid:** Add both `timeline_router` and `summary_router` to `backend/main.py`. Update version to `0.6.0` and `"phase": 6` in `/health`.

---

## Code Examples

### Timeline Observations Endpoint (recommended shape)

```python
# backend/api/timeline.py
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from utils.auth import get_current_user
from services.patient_query import get_observations_timeline

router = APIRouter()

class ObservationTimelineItem(BaseModel):
    observed_at: str | None
    value_num: float | None
    value_str: str | None
    unit: str | None
    ref_low: float | None
    ref_high: float | None
    flag: str | None
    document_id: str | None
    analyte_raw: str | None
    analyte_norm: str | None
    needs_review: bool

class ObservationTimelineResponse(BaseModel):
    analyte: str
    items: list[ObservationTimelineItem]

@router.get("/timeline/observations/{analyte}", response_model=ObservationTimelineResponse)
def get_observation_timeline(
    analyte: str,
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    user_id: str = Depends(get_current_user),
):
    items = get_observations_timeline(user_id, analyte, date_from, date_to)
    return ObservationTimelineResponse(analyte=analyte, items=items)
```

### Patient Summary Service (recommended shape)

```python
# backend/services/patient_query.py
import logging
from services.supabase_store import _get_client

_log = logging.getLogger(__name__)

def get_patient_summary(user_id: str) -> dict | None:
    """Query all patient tables and return structured aggregate. Soft-fail."""
    try:
        client = _get_client()
        conditions = _query_conditions(client, user_id)
        medications = _query_medications(client, user_id)
        allergies = _query_allergies(client, user_id)
        latest_labs = _query_latest_labs(client, user_id)
        return {
            "user_id": user_id,
            "active_conditions": conditions,
            "current_medications": medications,
            "allergies": allergies,
            "latest_labs": latest_labs,
        }
    except Exception as exc:
        _log.warning("patient_query.get_patient_summary failed user_id=%s: %s", user_id, exc)
        return None

def _query_latest_labs(client, user_id: str) -> list[dict]:
    """Return the most recent observation per normalized_analyte."""
    # Supabase doesn't support DISTINCT ON natively via REST — fetch all and
    # deduplicate in Python by keeping first occurrence per normalized_analyte
    # (rows already ordered desc by observed_date)
    res = client.table("patient_observations") \
        .select("normalized_analyte,raw_analyte,value_str,unit,reference_range,flag,needs_review,observed_date,document_id") \
        .eq("user_id", user_id) \
        .order("observed_date", desc=True) \
        .execute()
    seen: set[str] = set()
    result = []
    for row in (res.data or []):
        key = row["normalized_analyte"]
        if key not in seen:
            seen.add(key)
            result.append(_enrich_observation(row))
    return result
```

### Emergency Refactor Pattern

```python
# backend/services/emergency.py — refactored build_emergency_profile
def build_emergency_profile(user_id: str) -> EmergencyProfile | None:
    # Query patient tables (soft-fail per D-12)
    try:
        client = _get_client()
        conditions = _query_active_conditions(client, user_id)
        medications = _query_active_medications(client, user_id)
        allergies_raw = _query_allergies(client, user_id)
    except Exception as exc:
        _log.warning("emergency patient table query failed user_id=%s: %s", user_id, exc)
        conditions, medications, allergies_raw = [], [], []

    # Blood type: regex on full_text — unchanged (D-10)
    # ...

    # Return same EmergencyProfile shape (D-11)
    return EmergencyProfile(
        user_id=user_id,
        blood_type=blood_type,
        allergies=allergies,
        active_medications=medications,
        active_conditions=conditions,
        last_updated=last_updated,
    )
```

### Frontend PatientStructuredData Component (recommended shape)

```typescript
// frontend/components/dashboard/PatientStructuredData.tsx
"use client";

import { useEffect, useState } from "react";
import { getPatientSummary, type PatientSummaryResponse } from "@/lib/api";
import { Stethoscope, Pill, AlertTriangle, FlaskConical, Loader2, FileText, RefreshCw, ChevronRight } from "lucide-react";
import Link from "next/link";

// Local Section component (duplicated from PatientSummary.tsx — 14 lines, avoids export coupling)
function Section({ icon: Icon, title, color, children }: { ... }) { ... }

export function PatientStructuredData() {
  const [data, setData] = useState<PatientSummaryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  function load() {
    setLoading(true);
    setError("");
    getPatientSummary()
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }

  useEffect(() => { load(); }, []);

  // ... loading / error / empty states per UI-SPEC copywriting contract
  // ... four Section cards: Condições Ativas, Medicamentos em Uso, Alergias Conhecidas, Últimos Exames
}
```

### Dashboard page.tsx Addition

```tsx
// frontend/app/dashboard/page.tsx — add after existing PatientSummary block
import { PatientStructuredData } from "@/components/dashboard/PatientStructuredData";

// In return JSX, after the existing "Análise do Histórico" div:
{/* Dados Clínicos */}
<div>
  <div className="mb-4 flex items-center gap-2">
    <div className="rounded-lg bg-teal-50 p-1.5 text-teal-600">
      <Activity className="h-4 w-4" />
    </div>
    <h2 className="text-base font-semibold text-gray-800">Dados Clínicos</h2>
    <p className="text-xs text-gray-500">Informações estruturadas extraídas dos documentos.</p>
  </div>
  <PatientStructuredData />
</div>
```

---

## UI-SPEC Contract (from 06-UI-SPEC.md — HIGH confidence)

The UI-SPEC is approved and binding. Key constraints for implementation:

| Constraint | Requirement |
|-----------|-------------|
| No shadcn | Hand-written Tailwind utility classes only |
| Font weights | Exactly 2: 400 regular, 600 semibold. NO `font-bold` (700) |
| Section card | Reuse existing `Section` component pattern from `PatientSummary.tsx` |
| Observation row | New pattern: `flex items-center justify-between gap-2 py-1` with value + flag badge |
| Flag colors | H/HH → `bg-red-100 text-red-700`; L/LL → `bg-blue-100 text-blue-700`; normal → omit badge |
| needs_review | Amber dot `h-1.5 w-1.5 rounded-full bg-amber-400` with tooltip only — no blocking UI |
| Labs section color | `text-teal-600 bg-teal-50` (new tint — not used in existing LLM panel) |
| Refresh button | `text-xs text-gray-400 hover:text-gray-600`, min 44px touch target (`py-2.5`) |
| All copy | Brazilian Portuguese — see copywriting contract in UI-SPEC |

---

## Environment Availability

Step 2.6: SKIPPED — no external dependencies introduced in this phase. All tools (FastAPI, Supabase, React, lucide-react) are already installed and verified operational in Phases 1-5.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (already configured) |
| Config file | `backend/conftest.py` (root-level sys.path setup) |
| Quick run command | `cd backend && python -m pytest tests/timeline/ -x -q` |
| Full suite command | `cd backend && python -m pytest tests/ -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TIMELINE-01 | `get_observations_timeline()` returns rows sorted desc, filters by date range | unit | `pytest tests/timeline/test_patient_query.py::test_observations_sorted_desc -x` | Wave 0 |
| TIMELINE-01 | `get_observations_timeline()` applies `date_from`/`date_to` filters correctly | unit | `pytest tests/timeline/test_patient_query.py::test_observations_date_filter -x` | Wave 0 |
| TIMELINE-01 | `value_num` is parsed from `value_str` (float cast, None on failure) | unit | `pytest tests/timeline/test_patient_query.py::test_value_num_parsing -x` | Wave 0 |
| TIMELINE-02 | `get_patient_summary()` returns conditions, medications, allergies, latest_labs | unit | `pytest tests/timeline/test_patient_query.py::test_patient_summary_shape -x` | Wave 0 |
| TIMELINE-02 | `get_patient_summary()` deduplicates latest labs per analyte (most recent only) | unit | `pytest tests/timeline/test_patient_query.py::test_latest_labs_dedup -x` | Wave 0 |
| TIMELINE-02 | `build_emergency_profile()` queries patient tables, not document scan | unit | `pytest tests/timeline/test_emergency_refactor.py::test_queries_patient_tables -x` | Wave 0 |
| TIMELINE-02 | Emergency soft-fail: patient table error returns profile with empty lists, not 500 | unit | `pytest tests/timeline/test_emergency_refactor.py::test_soft_fail_on_table_error -x` | Wave 0 |
| TIMELINE-03 | Frontend: `getPatientSummary()` calls correct URL with auth header | manual smoke | n/a | n/a |

### Sampling Rate

- **Per task commit:** `cd backend && python -m pytest tests/timeline/ -x -q`
- **Per wave merge:** `cd backend && python -m pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `backend/tests/timeline/__init__.py` — package init
- [ ] `backend/tests/timeline/test_patient_query.py` — covers TIMELINE-01, TIMELINE-02 query logic
- [ ] `backend/tests/timeline/test_emergency_refactor.py` — covers TIMELINE-02 emergency refactor

---

## Sources

### Primary (HIGH confidence)

- `backend/services/patient_store.py` — exact column names and INSERT dicts for all 5 patient tables
- `backend/services/emergency.py` — full implementation of current document-scan pattern to be replaced
- `backend/models/emergency.py` — EmergencyProfile, Allergy, Medication models (unchanged by phase)
- `backend/api/analysis.py` — canonical pattern for authenticated GET endpoint
- `backend/api/emergency.py` — canonical pattern for router + helper function
- `frontend/components/dashboard/PatientSummary.tsx` — Section component, loading/error/refresh patterns
- `frontend/lib/api.ts` — getAnalysis() as model for new API client functions
- `frontend/app/dashboard/page.tsx` — exact integration point for new component
- `backend/main.py` — router registration pattern
- `backend/utils/auth.py` — get_current_user dependency
- `.planning/phases/06-patient-timeline-api-and-dashboard/06-UI-SPEC.md` — binding UI contract

### Secondary (MEDIUM confidence)

- `.planning/phases/02-longitudinal-patient-data-model/02-CONTEXT.md` — D-01 to D-17: dedup strategy, column semantics, alias table

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in use, no new installs
- Architecture patterns: HIGH — read directly from source files, not inferred
- Schema facts: HIGH — read from patient_store.py INSERT dicts; `value_num` gap confirmed by absence from dict
- Pitfalls: HIGH — derived from actual code inspection (emergency.py has no try/except, Section not exported)
- Frontend patterns: HIGH — read from PatientSummary.tsx and api.ts directly

**Research date:** 2026-04-08
**Valid until:** 2026-05-08 (stable stack, 30-day window)
