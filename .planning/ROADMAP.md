# Roadmap: UHR — Unified Health Record

**Created:** 2026-04-04
**Milestone:** 1.0 — Clinical Intelligence Platform
**Granularity:** Standard (5-8 phases, 3-5 plans each)

---

## Milestone 1 — Ingestion Foundation

> Fix the data quality problem at the source. Everything downstream depends on reliable text.

### Phase 1: Adaptive Text Extraction

**Goal:** Stop sending native-text PDFs through OCR. Detect, extract natively, score quality, and fall back to OCR only when necessary.

**Requirements:** INGEST-01, INGEST-02, INGEST-03, INGEST-04, INGEST-05, INGEST-06

**Plans:** 4/5 plans executed

Plans:
- [x] 01-PLAN-1-page-classifier.md — Add pymupdf; implement is_native_page() classifier (char count, image coverage, font sanity) ✓ 2026-04-05
- [ ] 01-PLAN-2-native-extraction-quality-score.md — Implement extract_text_native() and compute_quality_score() (4-signal weighted)
- [ ] 01-PLAN-3-adaptive-router.md — Wire adaptive routing into document_intelligence.py; preserve orchestrator interface
- [ ] 01-PLAN-4-metadata-storage.md — Add ExtractionMeta model; persist text_extraction_meta JSONB on every upload
- [ ] 01-PLAN-5-edge-cases.md — Handle password-protected, corrupt, QR code, AcroForm, and ICP-Brasil PDFs

**Done when:**
- Native-text PDFs extract without calling Azure Document Intelligence
- Quality score stored alongside every document
- Orchestrator receives the same interface — no breaking changes
- 10 test documents processed and metadata verified

---

### Phase 2: Longitudinal Patient Data Model

**Goal:** Promote structured extraction output from per-document JSONB blobs into first-class queryable patient tables.

**Requirements:** STORE-01, STORE-02, STORE-03

**Plans:** 3/3 plans executed

Plans:
- [x] 02-01-PLAN.md — Create 6 Postgres tables (5 patient + analyte_aliases) via Supabase migration with seed data; Pydantic models
- [x] 02-02-PLAN.md — Implement patient_store.py promotion functions per document family with dedup, alias lookup, conflict detection; unit tests
- [x] 02-03-PLAN.md — Wire promotion into upload pipeline after store_save; end-to-end verification

**Done when:**
- Upload of a lab PDF creates rows in `patient_observations`
- Upload of a clinical note creates rows in `patient_conditions` and `patient_medications`
- Duplicate upload of the same document does not create duplicate rows (dedup_key constraint)
- All 5 tables populated from the test document set

---

### Phase 3: Migration and Backfill

**Goal:** Bring all existing data into the new model — zero data left behind.

**Requirements:** STORE-04, STORE-05

**Plans:** 3/3 plans complete

Plans:
- [x] 03-01-PLAN.md — Create migrate_health_entries.py: map health_entries to patient tables with dry-run and unit tests (STORE-04)
- [x] 03-02-PLAN.md — Create backfill_patient_tables.py: iterate documents, promote structured_result with dry-run and unit tests (STORE-05)
- [x] 03-03-PLAN.md — Run both scripts against live DB, verify completeness, confirm idempotency (STORE-04, STORE-05)

**Done when:**
- All existing `health_entries` migrated with no data loss
- All documents with non-null `structured_result` have corresponding patient table rows
- Scripts are idempotent (safe to re-run)
- Old `health_entries` table kept as backup (not deleted)

---

## Milestone 2 — Retrieval & Patient Profile

> Make the data actually queryable. Replace BM25 fragments with structured, hybrid, intent-aware retrieval.

### Phase 4: Hybrid Search Index

**Goal:** Rebuild Azure AI Search index to support vector similarity, metadata filtering, and semantic ranking.

**Requirements:** RETRIEVE-01, RETRIEVE-02, RETRIEVE-03

**Plans:** 6/6 plans complete

Plans:
- [x] 04-01-PLAN.md — Wave 0 test stubs + Azure tier verification (RETRIEVE-01, RETRIEVE-02, RETRIEVE-03)
- [x] 04-02-PLAN.md — Index schema extension: content_vector, filterable metadata, semantic config (RETRIEVE-01)
- [x] 04-03-PLAN.md — Embeddings service: context_block.py + embeddings.py (RETRIEVE-02)
- [x] 04-04-PLAN.md — Indexer update: context block assembly + embedding in upload pipeline (RETRIEVE-02)
- [x] 04-05-PLAN.md — Retriever update: hybrid VectorizedQuery + semantic reranking (RETRIEVE-03)
- [x] 04-06-PLAN.md — Re-index script + execution: migrate all documents to hybrid index (RETRIEVE-01, RETRIEVE-02, RETRIEVE-03)

**Done when:**
- Hybrid query returns more relevant results than BM25 on 10 sample clinical queries
- All existing documents re-indexed with vectors
- No regression in existing chat functionality

---

### Phase 5: Query Routing and Context Assembly

**Goal:** Route queries intelligently (SQL vs. search) and inject structured clinical context instead of raw text fragments.

**Requirements:** RETRIEVE-04, RETRIEVE-05

**Plans:** 3/5 plans executed

Plans:
- [x] 05-01-PLAN.md — Wave 0 test stubs: test_router.py (11 stubs) + test_retriever.py new stub (RETRIEVE-04, RETRIEVE-05)
- [x] 05-02-PLAN.md — router.py core: RoutingResult, expand_abbreviations(), route_query(), SQL executor functions (RETRIEVE-04)
- [x] 05-03-PLAN.md — router.py chat assembler: _fetch_structured_result(), assemble_chat_block() per document family (RETRIEVE-05)
- [ ] 05-04-PLAN.md — retriever.py refactor: wire route_query + execute_sql_steps + assemble_chat_block, update SYSTEM_PROMPT (RETRIEVE-04, RETRIEVE-05)
- [ ] 05-05-PLAN.md — Unskip and implement all 12 test stubs; full suite green (RETRIEVE-04, RETRIEVE-05)

**Done when:**
- "What was my average HbA1c last year?" returns a SQL-computed answer
- "What did my cardiologist say?" retrieves narrative documents via hybrid search
- Context injected into Claude contains lab values with units and flags, not OCR fragments
- Chat quality verified on 15 sample queries covering all intent types

---

### Phase 6: Patient Timeline API and Dashboard

**Goal:** Expose patient-level aggregates via API and surface them in the frontend dashboard.

**Requirements:** TIMELINE-01, TIMELINE-02, TIMELINE-03

**Plans:**
1. Implement `api/timeline.py`: `GET /timeline/observations/{analyte}`, `GET /timeline/conditions`, `GET /timeline/medications` endpoints
2. Implement `GET /patient/summary` endpoint: active conditions, current medications, allergies, latest labs grouped by analyte
3. Refactor `services/emergency.py` to query new patient tables instead of scanning documents
4. Update frontend `app/dashboard/page.tsx` and `components/dashboard/PatientSummary.tsx` to display patient-level data
5. Update emergency profile page to use new aggregated data

**Done when:**
- Dashboard shows active conditions, current medications, and latest labs without querying individual documents
- Emergency profile built from patient tables (not document scan)
- Timeline endpoint returns observations for a given analyte sorted by date

---

## Milestone 3 — Clinical Intelligence

> Add reasoning. Go from "show me the data" to "help me understand it."

### Phase 7: Clinical Reasoning Engine

**Goal:** Generate structured case summaries and differential diagnoses from the patient profile.

**Requirements:** REASON-01 through REASON-06

**Plans:**
1. Define `ClinicalReasoningResult`, `DifferentialEntry`, `EvidenceReference`, `RelevantFinding` Pydantic schemas in `models/reasoning.py`
2. Implement patient block assembler: aggregate active conditions, medications, recent labs, recent imaging into structured prompt input (<8K tokens)
3. Implement `services/reasoning/summarizer.py`: Call 1 — generate case summary and key findings from patient block
4. Implement `services/reasoning/differentials.py`: Call 2 — generate three-tier differentials with evidence anchoring and contradicting evidence fields; use extended thinking if on direct Anthropic API
5. Implement output validation: citation accuracy check (verify cited document IDs exist), schema conformance, `is_outside_scope` guard
6. Expose `POST /reasoning/analyze` endpoint and wire into analysis page

**Done when:**
- Case summary generated from patient block with citations to specific documents
- Differentials include supporting AND contradicting evidence per entry
- Responses include contextual hedges (not boilerplate disclaimers)
- No differential cites a document that doesn't exist in the patient's record

---

### Phase 8: Security Hardening

**Goal:** Fix the critical security issues identified in the codebase audit before any broader exposure.

**Requirements:** SEC-01, SEC-02, SEC-03

**Plans:**
1. Add authentication to `GET /emergency/{user_id}`: token-based (UUID in query param acts as auth) OR require Bearer token — document the trade-off
2. Add production guard to `utils/auth.py`: if `USE_MOCK_AZURE=true` in a non-local environment, log a CRITICAL warning and optionally refuse to start
3. Add environment detection utility: distinguish `local`, `staging`, `production` from env vars; gate mock bypass on `local` only
4. Update `.env.example` and deployment documentation with explicit warnings about `USE_MOCK_AZURE`

**Done when:**
- Accessing `/emergency/{user_id}` without credentials returns 401
- Starting with `USE_MOCK_AZURE=true` and `ENV=production` logs CRITICAL warning
- `.env.example` documents the security risk of mock mode

---

## Phase Dependency Graph

```
Phase 1 (Extraction)
  └── Phase 2 (Patient Model)
        └── Phase 3 (Migration/Backfill)
              └── Phase 5 (Query Routing)  ←── Phase 4 (Hybrid Index)
                    └── Phase 6 (Timeline API)
                          └── Phase 7 (Reasoning)

Phase 8 (Security) ── independent, can run in parallel with Phase 4-6
```

## Milestone Summary

| Milestone | Phases | Focus |
|-----------|--------|-------|
| 1 — Ingestion Foundation | 1–3 | Fix text quality at the source; build patient data model |
| 2 — Retrieval & Profile | 4–6 | Hybrid search; patient timeline API and dashboard |
| 3 — Clinical Intelligence | 7–8 | Clinical reasoning; security hardening |

## Success Criteria (v1.0)

- [ ] Native-text PDFs extract without OCR; quality score stored for every document
- [ ] Patient profile queryable across all documents (labs, conditions, medications, allergies)
- [ ] Chat correctly answers "what was my HbA1c last year?" using patient table data
- [ ] Differentials generated with evidence citations tied to specific documents
- [ ] Emergency profile endpoint protected from unauthenticated access
- [ ] All existing documents backfilled into new patient tables

---
*Roadmap created: 2026-04-04*
*Phase 1 plans created: 2026-04-02*
*Phase 2 plans created: 2026-04-05*
*Phase 3 plans created: 2026-04-06*
*Phase 4 plans created: 2026-04-06*
*Phase 5 plans created: 2026-04-08*
