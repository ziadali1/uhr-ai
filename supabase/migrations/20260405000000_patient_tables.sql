-- supabase/migrations/20260405000000_patient_tables.sql
-- Phase 02: Longitudinal Patient Data Model
-- Creates 6 tables: 5 patient entity tables + analyte_aliases lookup

-- 1. patient_observations (D-01, D-03)
-- No composite UNIQUE constraint — dedup logic handled in application code per D-01
-- (conflicting values for same key → store both, flag newer with needs_review=true)
CREATE TABLE IF NOT EXISTS patient_observations (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id            TEXT NOT NULL,
    document_id        TEXT,
    normalized_analyte TEXT NOT NULL,
    raw_analyte        TEXT NOT NULL,
    value_str          TEXT,
    unit               TEXT,
    reference_range    TEXT,
    flag               TEXT CHECK (flag IN ('normal','high','low','borderline','critical')),
    observed_date      DATE,
    needs_review       BOOLEAN NOT NULL DEFAULT FALSE,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Non-unique index for fast dedup lookups (D-01, D-03)
CREATE INDEX IF NOT EXISTS idx_obs_dedup ON patient_observations (user_id, normalized_analyte, observed_date);

-- 2. patient_conditions (D-09, D-02)
CREATE TABLE IF NOT EXISTS patient_conditions (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id              TEXT NOT NULL,
    document_id          TEXT,
    raw_condition        TEXT NOT NULL,
    normalized_condition TEXT NOT NULL,
    clinical_status      TEXT CHECK (clinical_status IN ('active','resolved','suspected')),
    verification_status  TEXT CHECK (verification_status IN ('confirmed','provisional')),
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, normalized_condition)
);

-- 3. patient_medications (D-10, D-02)
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
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, normalized_medication)
);

-- 4. patient_allergies (D-11, D-02)
CREATE TABLE IF NOT EXISTS patient_allergies (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             TEXT NOT NULL,
    document_id         TEXT,
    raw_allergen        TEXT NOT NULL,
    normalized_allergen TEXT NOT NULL,
    reaction            TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, normalized_allergen)
);

-- 5. patient_imaging_findings (D-13)
CREATE TABLE IF NOT EXISTS patient_imaging_findings (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     TEXT NOT NULL,
    document_id TEXT,
    modality    TEXT,
    body_region TEXT,
    impression  TEXT,
    urgency     TEXT CHECK (urgency IN ('routine','urgent','critical')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 6. analyte_aliases (D-14)
CREATE TABLE IF NOT EXISTS analyte_aliases (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    raw_name       TEXT NOT NULL UNIQUE,
    canonical_name TEXT NOT NULL,
    unit_canonical TEXT
);

-- Seed data: common Brazilian lab analyte aliases (D-15)
-- Includes both accented and unaccented variants to handle inconsistent extraction
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
    ('triglicerideos', 'triglicerideos'),
    ('triglicerídeos', 'triglicerideos'),
    ('tsh', 'tsh'),
    ('t4 livre', 't4_livre'),
    ('sodio', 'sodio'),
    ('sódio', 'sodio'),
    ('potassio', 'potassio'),
    ('potássio', 'potassio'),
    ('pcr', 'proteina_c_reativa'),
    ('plaquetas', 'plaquetas'),
    ('leucocitos', 'leucocitos'),
    ('leucócitos', 'leucocitos'),
    ('hemacias', 'hemacias'),
    ('hemácias', 'hemacias')
ON CONFLICT (raw_name) DO NOTHING;
