# Phase 2: Longitudinal Patient Data Model - Research

**Researched:** 2026-04-05
**Domain:** Supabase PostgreSQL schema design, Python upsert patterns, promotion pipeline integration
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Observations dedup: `user_id + normalized_analyte + observed_date`. Identical value/unit → upsert. Conflicting value/unit → store both, set `needs_review = true` on the newer row.
- **D-02:** Conditions, medications, allergies: upsert on canonical name. Latest document wins. No conflict flagging.
- **D-03:** Dedup key for observations: composite unique constraint `(user_id, normalized_analyte, observed_date)`. Fallback normalization: lowercase+strip raw name if no alias found.
- **D-04:** Soft-fail. Promotion failure MUST NOT block document upload.
- **D-05:** On failure: log `document_id` + error details. Do not raise HTTP exception.
- **D-06:** Promotion must be idempotent. Use `ON CONFLICT DO UPDATE`, never blind inserts.
- **D-07:** Follow Phase 1 `text_extraction_meta` pattern (supabase_store.py lines 42–47): wrap in try/except, log silently, continue.
- **D-08:** Store both raw and normalized values for all patient entity types.
- **D-09:** `patient_conditions`: `raw_condition`, `normalized_condition`, `clinical_status` (active|resolved|suspected|null), `verification_status` (confirmed|provisional|null), `source_document_id`.
- **D-10:** `patient_medications`: `raw_medication`, `normalized_medication`, `dose`, `route`, `frequency`, `status` (active|stopped|null), `source_document_id`.
- **D-11:** `patient_allergies`: `raw_allergen`, `normalized_allergen`, `reaction`, `source_document_id`.
- **D-12:** No LOINC/SNOMED/RxNorm in v1. String-level normalization only.
- **D-13:** `patient_imaging_findings`: `modality`, `body_region`, `impression`, `urgency` (routine|urgent|critical|null), `source_document_id`.
- **D-14:** `analyte_aliases` is a Supabase table (not hardcoded). Schema: `id`, `raw_name` (unique), `canonical_name`, `unit_canonical` (nullable).
- **D-15:** Pre-seed with ~20 common Brazilian lab terms (Hb, Hemoglobina, HbA1c, hemoglobina glicada, glicose, glicemia, creatinina, ureia, colesterol total, LDL, HDL, triglicerídeos, TSH, T4 livre, sódio, potássio, PCR, plaquetas, leucócitos, hemácias).
- **D-16:** No LOINC codes in v1.
- **D-17:** Alias lookup is case-insensitive. If not found → `normalized_analyte = raw_name.lower().strip()`.

### Claude's Discretion

- Exact Pydantic model names and field ordering for the 5 new patient table models
- Supabase migration file structure and naming (follow existing conventions in codebase if any)
- Whether `patient_store.py` is a single file or split by domain (one function per family is acceptable)
- Internal promotion function signatures
- Exact logging format for soft-fail errors

### Deferred Ideas (OUT OF SCOPE)

- Full LOINC / SNOMED / RxNorm ontology mapping
- Review UI for `needs_review` flagged observations
- Migration of existing `health_entries` into new patient tables (Phase 3)
- Backfill of existing documents' structured_result (Phase 3)
- Cross-document entity linking
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| STORE-01 | System has 5 queryable Postgres tables for longitudinal patient data: `patient_observations`, `patient_conditions`, `patient_medications`, `patient_allergies`, `patient_imaging_findings` | Schema designed below; migration SQL documented with composite unique constraints and dedup_key columns |
| STORE-02 | System promotes structured extraction results into patient tables after every document upload | Integration point identified: `upload.py` line 116 after `store_save()`; soft-fail wrapper pattern from Phase 1 confirmed |
| STORE-03 | System deduplicates patient entities using tiered strategy (alias table → fallback → flag for review) | Supabase upsert API confirmed (`on_conflict` parameter); alias lookup pattern documented; needs_review flag approach verified |
</phase_requirements>

---

## Summary

Phase 2 takes the already-populated `documents.structured_result` JSONB column (written in Phase 1's pipeline) and promotes its contents into 6 purpose-built Postgres tables: 5 patient entity tables plus 1 `analyte_aliases` lookup. The structured source models (`StructuredLab`, `ClinicalNote`, `ImagingReport`, `MedicationDocument`) already exist in `backend/models/document.py` and contain well-typed fields — promotion is a mapping exercise, not a re-extraction.

The critical design constraint is idempotency: every insert must be an upsert using Supabase's `on_conflict` parameter, which maps directly to PostgreSQL `ON CONFLICT DO UPDATE`. The Supabase Python SDK 2.4.6 (installed) supports this via `.upsert(data, on_conflict="col1,col2").execute()`. The soft-fail pattern is already established in `supabase_store.py` lines 42–47 (Phase 1 precedent) and must be replicated exactly.

The analyte normalization path requires an `analyte_aliases` database lookup before inserting observations. This is the only external I/O in the promotion path beyond the patient table inserts themselves — the lookup must be cached per-request to avoid N+1 queries when a single lab report contains 20+ analytes.

**Primary recommendation:** Implement `services/patient_store.py` with one promotion function per document family, each using Supabase upserts with explicit `on_conflict` columns. Wire into `upload.py` as a single try/except block after `store_save()`. Create tables via a single Supabase migration SQL file seeded with the Brazilian analyte list.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| supabase-py | 2.4.6 (installed) | Postgres upsert via PostgREST | Already used in supabase_store.py; upsert with on_conflict supported |
| pydantic | 2.7.1 (installed) | Patient table models | Project standard; all models use pydantic 2.x |
| pytest | 8.2.0 (installed) | Unit tests for promotion logic | All Phase 1 tests use pytest; suite runs in 0.77s |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| python logging (stdlib) | built-in | Soft-fail error logging | Used for silent error capture in promotion path |
| uuid (stdlib) | built-in | Primary key generation | All existing tables use UUID PKs |

### No New Dependencies Required

All required libraries are already installed. No `pip install` step needed for this phase.

---

## Architecture Patterns

### Recommended Project Structure

```
backend/
├── services/
│   └── patient_store.py          # NEW: promotion functions per family
├── models/
│   └── patient.py                # NEW: Pydantic models for 5 patient tables
├── tests/
│   └── patient/
│       ├── __init__.py
│       └── test_patient_store.py # NEW: unit tests with fixture documents
supabase/
└── migrations/
    └── 20260405000000_patient_tables.sql  # NEW: 6 tables + seed data
```

Note: no existing `supabase/migrations/` directory was found in the repo — create it as the canonical home for migration files.

### Pattern 1: Supabase Upsert with on_conflict

**What:** Insert-or-update using `on_conflict` column list, so re-running promotion on the same document produces identical database state.

**When to use:** Every insert into patient tables — observations, conditions, medications, allergies, imaging_findings.

**Example (observations — conflict-flagging variant):**
```python
# Source: https://supabase.com/docs/reference/python/upsert
from services.supabase_store import _get_client  # reuse singleton

def _upsert_observation(row: dict) -> None:
    client = _get_client()
    # Attempt upsert; if values/units match, this is a no-op update
    client.table("patient_observations").upsert(
        row,
        on_conflict="user_id,normalized_analyte,observed_date",
    ).execute()
```

**Example (conditions/medications/allergies — latest-wins variant):**
```python
client.table("patient_conditions").upsert(
    row,
    on_conflict="user_id,normalized_condition",
).execute()
```

### Pattern 2: Soft-Fail Promotion Wrapper (Phase 1 Precedent)

**What:** Wrap the entire promotion call in try/except so any failure is logged but never surfaces as an HTTP error.

**When to use:** At the `upload.py` call site after `store_save()`.

**Example:**
```python
# upload.py — after line 116 (store_save call)
# Source: supabase_store.py lines 42-47 (Phase 1 pattern)
try:
    from services.patient_store import promote_to_patient_tables
    promote_to_patient_tables(
        doc_id=doc_id,
        user_id=user_id,
        structured_result=result.structured_result,
    )
except Exception as exc:
    import logging
    logging.getLogger(__name__).warning(
        "patient_store promotion failed doc_id=%s: %s", doc_id, exc
    )
```

### Pattern 3: Analyte Alias Lookup with Per-Call Cache

**What:** Fetch the entire `analyte_aliases` table once at the start of promotion, then resolve all analytes from the in-memory dict.

**When to use:** Inside `promote_lab()` / `promote_observations()`.

**Example:**
```python
def _load_aliases(client) -> dict[str, str]:
    """Returns {raw_name_lower: canonical_name}."""
    res = client.table("analyte_aliases").select("raw_name,canonical_name").execute()
    return {row["raw_name"].lower(): row["canonical_name"] for row in (res.data or [])}

def _normalize_analyte(raw: str, aliases: dict[str, str]) -> str:
    return aliases.get(raw.strip().lower(), raw.strip().lower())
```

### Pattern 4: Conflict Detection for Observations (needs_review flag)

**What:** D-01 requires that if the same `(user_id, normalized_analyte, observed_date)` already exists with a *different* value or unit, both rows are stored and the newer one is flagged.

**Implementation note:** Supabase upsert with `on_conflict` will UPDATE the existing row if there's a conflict. To implement the "store both + flag" behavior, the promotion function must:
1. Check if a row already exists for the dedup key.
2. If it exists and values differ → insert a NEW row (different UUID) with `needs_review=True`.
3. If it exists and values are identical → upsert (effectively a no-op).
4. If it does not exist → plain upsert (insert).

This means `patient_observations` does NOT use a single `on_conflict` upsert for all cases — the conflict-detection path requires a pre-check query followed by a conditional insert.

**Example:**
```python
def _promote_observation(client, row: dict, aliases: dict) -> None:
    existing = (
        client.table("patient_observations")
        .select("id,value_str,unit")
        .eq("user_id", row["user_id"])
        .eq("normalized_analyte", row["normalized_analyte"])
        .eq("observed_date", row["observed_date"])
        .execute()
    )
    if existing.data:
        ex = existing.data[0]
        if ex["value_str"] == row["value_str"] and ex["unit"] == row["unit"]:
            return  # identical — no-op
        else:
            row["needs_review"] = True
            # Fall through to plain insert (new UUID already in row)
    client.table("patient_observations").insert(row).execute()
```

### Anti-Patterns to Avoid

- **Blind INSERT without conflict handling:** Will fail with unique constraint violation on re-upload. Every insert must be upsert or pre-checked.
- **N+1 alias lookups:** Fetching `analyte_aliases` per analyte per document. Load once per promotion call.
- **Raising exceptions in promotion:** Must be soft-fail. Never propagate exceptions out of `promote_to_patient_tables()`.
- **Merging conflicting lab values:** D-01 explicitly forbids automatic merging. Store both, flag the newer.
- **Using `INSERT ... ON CONFLICT DO NOTHING` for conditions/medications:** D-02 requires latest document wins (UPDATE), not ignore. Use `DO UPDATE SET ...`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Upsert with conflict resolution | Custom SELECT + conditional INSERT/UPDATE logic | `supabase.table(...).upsert(row, on_conflict="cols").execute()` | Supabase SDK translates directly to PostgreSQL ON CONFLICT; single round-trip |
| Singleton DB client | New client per call | `_get_client()` from `supabase_store.py` | Already implemented; reuse pattern |
| Case-insensitive alias lookup | Custom normalization function | `.lower().strip()` + pre-loaded dict | Sufficient for v1; D-17 explicitly scopes this |
| Date parsing | Custom DD/MM/YYYY parser | `dateutil.parser.parse()` or explicit `strptime("%d/%m/%Y")` | Brazilian format; stdlib handles this |

**Key insight:** The Supabase Python SDK's `.upsert()` method with `on_conflict` covers 80% of the dedup logic. The only exception is the observations conflict-detection path (D-01) which requires a pre-check.

---

## Runtime State Inventory

Step 2.5: SKIPPED — this is a greenfield schema addition phase. No renames, no refactors, no string replacements. New tables and a new service file are being created; no existing runtime state is being migrated (that is Phase 3).

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| supabase-py | Patient table upserts | Yes | 2.4.6 | — |
| pydantic | Patient table models | Yes | 2.7.1 | — |
| pytest | Unit tests | Yes | 8.2.0 | — |
| PostgreSQL (Supabase) | Migration execution | Remote (Supabase cloud) | — | Must run migration via Supabase Dashboard or CLI |
| Supabase CLI | Migration file apply | Not checked locally | — | Apply via Supabase Dashboard SQL editor |

**Missing dependencies with no fallback:**
- None blocking code implementation. The Supabase migration must be applied to the remote database before the promotion code runs end-to-end. Tests are written to mock the Supabase client, so they run without the live DB.

**Missing dependencies with fallback:**
- Supabase CLI: if not installed, the migration SQL can be applied via the Supabase Dashboard SQL editor directly. Document both paths in the plan.

---

## Common Pitfalls

### Pitfall 1: Brazilian Date Format (DD/MM/YYYY)

**What goes wrong:** `StructuredLab.collection_date` may be extracted as `"15/03/2025"`. Treating it as ISO `"2025-03-15"` will fail or silently produce a wrong date.

**Why it happens:** The LLM extracts dates in the format they appear in the Portuguese document. Brazilian lab reports use DD/MM/YYYY.

**How to avoid:** Parse with `datetime.strptime(date_str, "%d/%m/%Y")` and convert to ISO before inserting. Wrap in try/except and fall back to `None` for unparseable dates (don't block promotion on a bad date string).

**Warning signs:** `datetime.fromisoformat()` raises `ValueError` for DD/MM/YYYY strings.

### Pitfall 2: `observed_date` Uniqueness Constraint Requires a Concrete Date

**What goes wrong:** Dedup key is `(user_id, normalized_analyte, observed_date)`. If `collection_date` is `None`, the date column is NULL — and `NULL != NULL` in SQL, so every upload of the same document creates a new row.

**Why it happens:** Not all lab reports include a collection date; `StructuredLab.collection_date` is `str | None`.

**How to avoid:** When `collection_date` is None, fall back to the document's `upload_date` (available as a parameter to the promotion function). This gives a concrete date and makes dedup reliable.

**Warning signs:** Duplicate rows in `patient_observations` with `observed_date IS NULL`.

### Pitfall 3: `structured_result.structured_data` is a Raw Dict

**What goes wrong:** `StructuredResult.structured_data` is typed as `dict[str, Any]`, not a typed Pydantic model. Accessing `.findings` on it will raise `AttributeError`.

**Why it happens:** The structured_data field is polymorphic — different families use different schemas. It's stored as a plain dict, not a typed object.

**How to avoid:** Re-parse into the correct typed model based on `document_family`. Example:
```python
from models.document import StructuredLab
if structured_result.document_family == "structured_lab":
    lab = StructuredLab(**structured_result.structured_data)
    for finding in lab.findings:
        ...
```

**Warning signs:** `AttributeError: 'dict' object has no attribute 'findings'`.

### Pitfall 4: Supabase `on_conflict` Requires Exact Column Name Match

**What goes wrong:** Passing `on_conflict="user_id, normalized_analyte"` (with spaces) may not match the constraint name as registered in PostgREST.

**Why it happens:** PostgREST uses the comma-separated column list to identify the constraint. Extra spaces can cause "no unique or exclusion constraint" errors in some SDK versions.

**How to avoid:** Use no spaces: `on_conflict="user_id,normalized_analyte,observed_date"`. Verify constraint names in the migration SQL match exactly.

**Warning signs:** Supabase returns HTTP 409 with "no unique or exclusion constraint matching the ON CONFLICT specification".

### Pitfall 5: `ClinicalNote` Mixes Conditions and Allergies in List[str]

**What goes wrong:** `ClinicalNote.diagnoses` and `ClinicalNote.allergies` are `list[str]`, not typed objects. The promotion function must iterate these lists and derive `raw_condition`/`raw_allergen` values.

**Why it happens:** `ClinicalNote` was designed for LLM extraction, not structured storage. It uses flat string lists.

**How to avoid:** When promoting a `ClinicalNote`, iterate each string, use it as `raw_condition`, normalize to `normalized_condition`, and upsert into `patient_conditions`. Similarly for `allergies` → `patient_allergies`.

**Warning signs:** Only conditions from `MedicationDocument` are being stored; clinical note diagnoses are silently dropped.

---

## Code Examples

### Full Promotion Dispatch Pattern

```python
# backend/services/patient_store.py
# Source: models/document.py + supabase_store.py patterns

import logging
from models.document import StructuredResult, StructuredLab, ClinicalNote, MedicationDocument, ImagingReport
from services.supabase_store import _get_client

_log = logging.getLogger(__name__)


def promote_to_patient_tables(doc_id: str, user_id: str, structured_result: StructuredResult | None) -> None:
    """Promote structured_result into patient tables. Soft-fail: never raises."""
    if structured_result is None:
        return
    try:
        client = _get_client()
        family = structured_result.document_family
        data = structured_result.structured_data

        if family == "structured_lab":
            _promote_lab(client, doc_id, user_id, StructuredLab(**data))
        elif family == "clinical_narrative":
            _promote_clinical(client, doc_id, user_id, ClinicalNote(**data))
        elif family == "medication_document":
            _promote_medications(client, doc_id, user_id, MedicationDocument(**data))
        elif family == "imaging_narrative":
            _promote_imaging(client, doc_id, user_id, ImagingReport(**data))
        # unknown family: skip silently

    except Exception as exc:
        _log.warning("patient_store promotion failed doc_id=%s: %s", doc_id, exc)
```

### Migration SQL Structure

```sql
-- supabase/migrations/20260405000000_patient_tables.sql

-- 1. patient_observations
CREATE TABLE IF NOT EXISTS patient_observations (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id          TEXT NOT NULL,
    document_id      TEXT,
    normalized_analyte TEXT NOT NULL,
    raw_analyte      TEXT NOT NULL,
    value_str        TEXT,
    unit             TEXT,
    reference_range  TEXT,
    flag             TEXT CHECK (flag IN ('normal','high','low','borderline','critical')),
    observed_date    DATE,
    needs_review     BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE (user_id, normalized_analyte, observed_date)
);

-- 2. patient_conditions
CREATE TABLE IF NOT EXISTS patient_conditions (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id              TEXT NOT NULL,
    document_id          TEXT,
    raw_condition        TEXT NOT NULL,
    normalized_condition TEXT NOT NULL,
    clinical_status      TEXT CHECK (clinical_status IN ('active','resolved','suspected')),
    verification_status  TEXT CHECK (verification_status IN ('confirmed','provisional')),
    UNIQUE (user_id, normalized_condition)
);

-- 3. patient_medications
CREATE TABLE IF NOT EXISTS patient_medications (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id               TEXT NOT NULL,
    document_id           TEXT,
    raw_medication        TEXT NOT NULL,
    normalized_medication TEXT NOT NULL,
    dose                  TEXT,
    route                 TEXT,
    frequency             TEXT,
    status                TEXT CHECK (status IN ('active','stopped')),
    UNIQUE (user_id, normalized_medication)
);

-- 4. patient_allergies
CREATE TABLE IF NOT EXISTS patient_allergies (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id            TEXT NOT NULL,
    document_id        TEXT,
    raw_allergen       TEXT NOT NULL,
    normalized_allergen TEXT NOT NULL,
    reaction           TEXT,
    UNIQUE (user_id, normalized_allergen)
);

-- 5. patient_imaging_findings
CREATE TABLE IF NOT EXISTS patient_imaging_findings (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     TEXT NOT NULL,
    document_id TEXT,
    modality    TEXT,
    body_region TEXT,
    impression  TEXT,
    urgency     TEXT CHECK (urgency IN ('routine','urgent','critical'))
);

-- 6. analyte_aliases
CREATE TABLE IF NOT EXISTS analyte_aliases (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    raw_name       TEXT NOT NULL UNIQUE,
    canonical_name TEXT NOT NULL,
    unit_canonical TEXT
);

-- Seed data: common Brazilian lab analytes
INSERT INTO analyte_aliases (raw_name, canonical_name) VALUES
    ('hb', 'hemoglobina'),
    ('hemoglobina', 'hemoglobina'),
    ('hba1c', 'hemoglobina_glicada'),
    ('hemoglobina glicada', 'hemoglobina_glicada'),
    ('glicose', 'glicose'),
    ('glicemia', 'glicose'),
    ('creatinina', 'creatinina'),
    ('ureia', 'ureia'),
    ('colesterol total', 'colesterol_total'),
    ('ldl', 'ldl'),
    ('hdl', 'hdl'),
    ('triglicerídeos', 'triglicerideos'),
    ('triglicerídeos', 'triglicerideos'),
    ('tsh', 'tsh'),
    ('t4 livre', 't4_livre'),
    ('sódio', 'sodio'),
    ('potássio', 'potassio'),
    ('pcr', 'proteina_c_reativa'),
    ('plaquetas', 'plaquetas'),
    ('leucócitos', 'leucocitos'),
    ('hemácias', 'hemacias')
ON CONFLICT (raw_name) DO NOTHING;
```

### Unit Test Pattern (following Phase 1 conventions)

```python
# backend/tests/patient/test_patient_store.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from unittest.mock import MagicMock, patch
from models.document import StructuredResult, StructuredLab, LabFinding


def _make_lab_structured_result(findings, collection_date="15/03/2025"):
    return StructuredResult(
        document_family="structured_lab",
        structured_data=StructuredLab(
            collection_date=collection_date,
            findings=findings,
        ).model_dump(),
    )


def test_promote_lab_inserts_observations():
    result = _make_lab_structured_result([
        LabFinding(name="Glicose", value="95", unit="mg/dL", flag="normal")
    ])
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
    mock_client.table.return_value.upsert.return_value.execute.return_value.data = [{"id": "abc"}]

    with patch("services.patient_store._get_client", return_value=mock_client):
        from services.patient_store import promote_to_patient_tables
        promote_to_patient_tables("doc-1", "user-1", result)

    mock_client.table.assert_called()


def test_promote_does_not_raise_on_exception():
    """Soft-fail: promotion must never propagate exceptions."""
    result = _make_lab_structured_result([
        LabFinding(name="Glicose", value="95", unit="mg/dL")
    ])
    with patch("services.patient_store._get_client", side_effect=RuntimeError("DB down")):
        from services.patient_store import promote_to_patient_tables
        # Must not raise
        promote_to_patient_tables("doc-1", "user-1", result)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Store all data as JSONB per document | Promote to first-class queryable rows | This phase | Enables SQL aggregation, timelines, dedup |
| No patient-level model | 5 dedicated patient tables + analyte_aliases | This phase | Foundation for Phases 3–7 |
| `supabase-py` `.insert()` only | `.upsert(on_conflict="cols")` | SDK 2.x | Idempotent promotion without custom conflict logic |

**Deprecated/outdated:**
- `analysis.py` iterating `medical_entities` for patient profile: will be replaced in Phases 3/6 by queries against new patient tables. Do not change in this phase.

---

## Open Questions

1. **`observed_date` type: `DATE` vs `TIMESTAMPTZ`**
   - What we know: Brazilian lab reports provide collection date at day granularity (no time). The research document uses `TIMESTAMPTZ` but the dedup key only needs date precision.
   - What's unclear: Whether storing as `DATE` vs `TIMESTAMPTZ` matters for Phase 6 timelines.
   - Recommendation: Use `DATE` for `observed_date` in `patient_observations` — it directly matches the dedup key semantics (D-03: `observed_date` not `observed_at`) and avoids timezone ambiguity in Brazilian date parsing.

2. **`user_id` column type: `TEXT` vs `UUID`**
   - What we know: `documents.user_id` is stored as `TEXT` in `supabase_store.py` (string passed as-is). The research schema uses `UUID REFERENCES auth.users(id)` but the existing codebase uses `TEXT`.
   - What's unclear: Whether the project uses Supabase Auth UUID user IDs or arbitrary string IDs.
   - Recommendation: Use `TEXT NOT NULL` to match the existing `health_entries` and `documents` pattern. Avoids FK constraint failures if user_id is a mock string in test environments.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.2.0 |
| Config file | none (pytest.ini not present; tests discovered by default) |
| Quick run command | `cd backend && python -m pytest tests/patient/ -v` |
| Full suite command | `cd backend && python -m pytest tests/ -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| STORE-01 | 5 patient tables created by migration SQL | manual (SQL DDL) | N/A — migration applied to Supabase | N/A |
| STORE-02 | `promote_to_patient_tables()` called after upload; lab PDF creates `patient_observations` rows | unit | `cd backend && python -m pytest tests/patient/test_patient_store.py -x` | Wave 0 |
| STORE-02 | Clinical note upload creates `patient_conditions` and `patient_medications` rows | unit | same | Wave 0 |
| STORE-02 | Promotion failure does not block upload (soft-fail) | unit | same | Wave 0 |
| STORE-03 | Duplicate upload of same document does not create duplicate rows | unit | same | Wave 0 |
| STORE-03 | Conflicting lab values for same analyte/date → second row flagged `needs_review=True` | unit | same | Wave 0 |
| STORE-03 | Analyte alias lookup is case-insensitive; unknown analytes fall back to lowercased name | unit | same | Wave 0 |

### Sampling Rate

- **Per task commit:** `cd backend && python -m pytest tests/patient/ -x`
- **Per wave merge:** `cd backend && python -m pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `backend/tests/patient/__init__.py` — package marker
- [ ] `backend/tests/patient/test_patient_store.py` — covers STORE-02, STORE-03 (7 test cases above)
- [ ] No framework install needed — pytest already installed

---

## Sources

### Primary (HIGH confidence)

- Supabase Python SDK 2.4.6 installed — verified via `python -c "import supabase; print(supabase.__version__)"`
- `backend/models/document.py` — direct read; source model field names verified
- `backend/services/supabase_store.py` — direct read; singleton client pattern and soft-fail pattern (lines 42–47) verified
- `backend/api/upload.py` — direct read; integration point at line 116 confirmed
- `backend/services/health_store.py` — direct read; existing patient data patterns referenced
- [Supabase Python Upsert Docs](https://supabase.com/docs/reference/python/upsert) — `on_conflict` parameter and comma-separated column format verified
- `.planning/research/patient-profile.md` — project's own prior research; schema design cross-referenced

### Secondary (MEDIUM confidence)

- pytest 8.2.0 test suite run — 36 tests pass, confirms test infrastructure is healthy and can be extended
- [Supabase upsert on_conflict discussion](https://github.com/orgs/supabase/discussions/18503) — community confirmation that spaces in `on_conflict` column list can cause issues

### Tertiary (LOW confidence)

- None — all critical claims verified against code or official docs.

---

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH — all libraries are already installed and in active use; versions verified from requirements.txt and Python import
- Architecture: HIGH — source models read directly from document.py; integration point verified from upload.py; upsert API verified from official docs
- Pitfalls: HIGH — date format pitfall verified from ClinicalNote/StructuredLab field types; dict-not-model pitfall verified from StructuredResult.structured_data typing; conflict semantics verified from Supabase docs
- Test patterns: HIGH — Phase 1 test files read directly; framework confirmed running

**Research date:** 2026-04-05
**Valid until:** 2026-05-05 (stable stack; Supabase SDK API is stable)
