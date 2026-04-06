# Research: Longitudinal Patient Data Modeling

## Core Gap

The extraction pipeline is already strong — family-specific LLM extraction produces well-structured `LabFinding`, `MedicationEntry`, `ClinicalNote`, and `ImagingReport` objects. The problem is that all this data stays **locked inside `structured_result` JSONB per document** and is never promoted into first-class queryable rows.

`analysis.py` illustrates the consequence: it iterates every document's `medical_entities` list and deduplicates by lowercased string — there is no patient-level model, only a document-level model.

## Recommended Schema: 5 New Postgres Tables

```sql
-- Lab results / vital measurements / any quantitative observation
CREATE TABLE patient_observations (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID NOT NULL REFERENCES auth.users(id),
    document_id  UUID REFERENCES documents(id),        -- source document
    analyte_norm TEXT NOT NULL,                        -- canonical name (e.g. "hemoglobin_a1c")
    analyte_raw  TEXT NOT NULL,                        -- original text from doc
    loinc_code   TEXT,                                 -- when mappable
    value_num    NUMERIC,                              -- NULL for qualitative
    value_str    TEXT,                                 -- qualitative or combined
    unit         TEXT,
    ref_low      NUMERIC,
    ref_high     NUMERIC,
    flag         TEXT CHECK (flag IN ('normal','low','high','critical_low','critical_high')),
    observed_at  TIMESTAMPTZ NOT NULL,
    dedup_key    TEXT GENERATED ALWAYS AS (
                   md5(user_id::text || analyte_norm || observed_at::date::text)
                 ) STORED,
    UNIQUE (dedup_key)
);

-- Diagnoses and clinical conditions
CREATE TABLE patient_conditions (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID NOT NULL REFERENCES auth.users(id),
    document_id         UUID REFERENCES documents(id),
    condition_norm      TEXT NOT NULL,                 -- canonical name
    condition_raw       TEXT NOT NULL,                 -- as it appeared
    icd10_code          TEXT,
    clinical_status     TEXT CHECK (clinical_status IN ('active','resolved','remission','unknown')),
    verification_status TEXT CHECK (verification_status IN ('confirmed','provisional','refuted')),
    onset_at            TIMESTAMPTZ,
    abatement_at        TIMESTAMPTZ,
    dedup_key           TEXT GENERATED ALWAYS AS (
                          md5(user_id::text || condition_norm)
                        ) STORED,
    UNIQUE (dedup_key)
);

-- Medications (prescribed, current, historical)
CREATE TABLE patient_medications (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       UUID NOT NULL REFERENCES auth.users(id),
    document_id   UUID REFERENCES documents(id),
    med_norm      TEXT NOT NULL,
    med_raw       TEXT NOT NULL,
    dose          TEXT,
    route         TEXT,
    frequency     TEXT,
    status        TEXT CHECK (status IN ('active','completed','stopped','unknown')),
    prescribed_at TIMESTAMPTZ,
    dedup_key     TEXT GENERATED ALWAYS AS (
                    md5(user_id::text || med_norm)
                  ) STORED,
    UNIQUE (dedup_key)
);

-- Allergies and intolerances
CREATE TABLE patient_allergies (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES auth.users(id),
    document_id     UUID REFERENCES documents(id),
    substance_norm  TEXT NOT NULL,
    substance_raw   TEXT NOT NULL,
    reaction        TEXT,
    severity        TEXT CHECK (severity IN ('mild','moderate','severe','unknown')),
    dedup_key       TEXT GENERATED ALWAYS AS (
                      md5(user_id::text || substance_norm)
                    ) STORED,
    UNIQUE (dedup_key)
);

-- Imaging findings
CREATE TABLE patient_imaging_findings (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID NOT NULL REFERENCES auth.users(id),
    document_id  UUID REFERENCES documents(id),
    modality     TEXT,                                 -- e.g. "xray", "mri", "ct"
    body_site    TEXT,
    impression   TEXT,
    findings_raw TEXT,
    performed_at TIMESTAMPTZ,
    is_normal    BOOLEAN
);
```

## Deduplication Strategy (Tiered)

1. **LOINC code matching** — when the LLM can map to a LOINC code, exact match
2. **`analyte_aliases` lookup table** — maps Portuguese lab name variants to canonical names (e.g. `"hemoglobina glicada"` → `"hemoglobin_a1c"`). More reliable than fuzzy matching for this domain.
3. **Fuzzy matching as last resort** — with a `needs_review` flag set

**Dedup key construction:**
- Observations: `hash(user_id + analyte_norm + observed_date)` — preserves trends, prevents exact duplicates
- Conditions/medications: `hash(user_id + normalized_name)` with upsert semantics (UPDATE on conflict to latest document reference)

## Temporal Modeling

- `onset_at` / `abatement_at` + `clinical_status` supports "active as of date X" queries cleanly
- OCR-extracted dates require validation before storage (Brazilian DD/MM/YYYY format, obviously invalid values)
- For conditions without explicit dates, use document `created_at` as fallback `onset_at`

## Hybrid Retrieval Intent Routing

An intent classifier routes queries to the right channel:

| Query type | Example | Route |
|------------|---------|-------|
| Structured / quantitative | "what is my HbA1c trend?" | SQL on `patient_observations` |
| Temporal / status | "what medications am I currently on?" | SQL on `patient_medications` |
| Narrative / contextual | "what did my cardiologist say?" | Azure AI Search RAG |
| Mixed | "was my kidney function normal after the antibiotic?" | Both, merge into prompt |

## Migration: Existing `health_entries`

Existing manual entries map directly:
- `medication_current` → `patient_medications (status='active')`
- `medication_past` → `patient_medications (status='completed')`
- `complaint` → `patient_conditions (verification_status='provisional')`
- `allergy` → `patient_allergies`

## Implementation Sequence (Non-Breaking)

All steps can be done without changing existing API contracts. First visible user-facing change happens when `analysis.py` and emergency card are refactored to query the new tables.

1. Add 5 new tables via migration
2. Write normalization + deduplication utilities
3. Wire promotion step into upload pipeline (after existing extraction)
4. Backfill existing documents' structured_result JSONB into new tables
5. Migrate existing `health_entries` records
6. Refactor `analysis.py` and emergency profile to query new tables
7. Build longitudinal query API endpoints

## Key Pitfalls

- **Date parsing:** Brazilian format (DD/MM/YYYY) conflicts with ISO format — always parse explicitly
- **Unit normalization:** `mg/dL` vs `mmol/L` for glucose — store raw unit, normalize separately
- **Missing dates:** many lab reports don't include the collection date — fall back to document date
- **Duplicate uploads:** same document uploaded twice creates duplicate observations — dedup_key handles this
- **Partial extraction:** LLM may miss some values — design promotion as additive, never replacing existing rows with NULLs
