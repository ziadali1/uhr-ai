# Requirements: UHR — Unified Health Record

**Defined:** 2026-04-04
**Core Value:** A patient's complete medical history — reliably extracted, reliably retrievable, and intelligently reasoned over.

## v1 Requirements

### Ingestion

- [x] **INGEST-01**: System detects whether a PDF has native text (character density, image coverage, font analysis) before routing to OCR — completed 01-01 (2026-04-05)
- [x] **INGEST-02**: System extracts text natively from native-text PDFs using PyMuPDF when quality score ≥ 0.65
- [x] **INGEST-03**: System falls back to Azure Document Intelligence OCR when native extraction is absent or low quality
- [x] **INGEST-04**: System computes a deterministic quality score [0,1] for each extracted text version
- [ ] **INGEST-05**: System stores extraction metadata (method, quality score, page strategies, library version) with each document in `text_extraction_meta` JSONB column
- [ ] **INGEST-06**: System handles medical PDF edge cases: password-protected, corrupt, AcroForm fields, ICP-Brasil signed PDFs

### Patient Data Model

- [ ] **STORE-01**: System has 5 queryable Postgres tables for longitudinal patient data: `patient_observations`, `patient_conditions`, `patient_medications`, `patient_allergies`, `patient_imaging_findings`
- [ ] **STORE-02**: System promotes structured extraction results into patient tables after every document upload
- [ ] **STORE-03**: System deduplicates patient entities across documents using tiered strategy (LOINC → alias table → fuzzy → flag for review)
- [ ] **STORE-04**: System migrates existing manual `health_entries` records into new patient tables without data loss
- [ ] **STORE-05**: System backfills existing documents' `structured_result` JSONB into new patient tables

### Retrieval

- [ ] **RETRIEVE-01**: Azure AI Search index includes vector fields (1536-dim, HNSW), filterable metadata (`document_family`, `collection_date`, `document_subtype`), and semantic configuration
- [ ] **RETRIEVE-02**: System generates embeddings from structured context blocks (not raw text) on each document upload
- [ ] **RETRIEVE-03**: Chat retrieval uses hybrid search (vector + keyword + RRF) instead of BM25-only
- [ ] **RETRIEVE-04**: System classifies query intent and routes numeric/aggregation queries to Supabase SQL, narrative queries to Azure AI Search
- [ ] **RETRIEVE-05**: Context injected into Claude uses structured entity blocks (lab values, flags, summaries) not 500-char raw text truncations

### Patient Timeline

- [ ] **TIMELINE-01**: API exposes patient observation timeline (lab values by analyte over time, filterable by date range)
- [ ] **TIMELINE-02**: API exposes active conditions, current medications, and allergies as patient-level aggregates (not per-document)
- [ ] **TIMELINE-03**: Frontend dashboard displays longitudinal lab trends and active clinical status

### Clinical Reasoning

- [ ] **REASON-01**: System generates structured case summaries from the patient block (conditions, medications, recent labs, recent imaging)
- [ ] **REASON-02**: System generates differential diagnosis candidates classified into three tiers: most likely, must not miss, possible
- [ ] **REASON-03**: Each differential entry cites specific patient data points (document ID, value, date) as evidence
- [ ] **REASON-04**: System uses `ClinicalReasoningResult` structured output schema with `EvidenceReference`, `DifferentialEntry`, `RelevantFinding`
- [ ] **REASON-05**: Responses include contextual uncertainty hedges embedded in the text (not boilerplate disclaimers)
- [ ] **REASON-06**: System includes `contradicting_evidence` field per differential to counter LLM sycophancy

### Security

- [ ] **SEC-01**: Emergency profile endpoint (`GET /emergency/{user_id}`) requires authentication or is protected by rate limiting + token
- [ ] **SEC-02**: Mock auth bypass (`USE_MOCK_AZURE=true`) is explicitly disabled in production environment and documented in deployment guide
- [ ] **SEC-03**: Deployment documentation warns about `USE_MOCK_AZURE` default and its auth implications

## v2 Requirements

### Anonymization

- **ANON-01**: PII anonymizer pipeline is called during document upload before storing raw text
- **ANON-02**: System stores anonymized version alongside original in blob storage

### Frontend Visualization

- **VIZ-01**: Lab trend chart (e.g., HbA1c over time) in frontend dashboard
- **VIZ-02**: Medication timeline visualization (active/stopped/past)
- **VIZ-03**: Exportable patient summary PDF

### Advanced Retrieval

- **ADV-01**: Query rewriting with Portuguese medical abbreviation expansion (HbA1c → hemoglobina glicada, PA → pressão arterial)
- **ADV-02**: Cross-document comparison (same lab test across multiple reports)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Custom ML model training | No training infra; use Azure APIs + Anthropic Claude only |
| Definitive clinical diagnoses | Copilot framing — assists, never decides; liability risk |
| Multi-user / shared records | Single patient, single user; adds auth complexity out of scope |
| Real-time device/sensor integration | Document-based only; streaming data is a different product |
| Billing, scheduling, EHR integration | Practice management is a separate product category |
| FHIR wire format compliance | Borrow vocabulary, not the spec; implementation cost not justified |
| HIPAA compliance infrastructure | Personal use; compliance certification is out of scope |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| INGEST-01 | Phase 1 | Pending |
| INGEST-02 | Phase 1 | Complete |
| INGEST-03 | Phase 1 | Complete |
| INGEST-04 | Phase 1 | Complete |
| INGEST-05 | Phase 1 | Pending |
| INGEST-06 | Phase 1 | Pending |
| STORE-01 | Phase 2 | Pending |
| STORE-02 | Phase 2 | Pending |
| STORE-03 | Phase 2 | Pending |
| STORE-04 | Phase 3 | Pending |
| STORE-05 | Phase 3 | Pending |
| RETRIEVE-01 | Phase 4 | Pending |
| RETRIEVE-02 | Phase 4 | Pending |
| RETRIEVE-03 | Phase 4 | Pending |
| RETRIEVE-04 | Phase 5 | Pending |
| RETRIEVE-05 | Phase 5 | Pending |
| TIMELINE-01 | Phase 6 | Pending |
| TIMELINE-02 | Phase 6 | Pending |
| TIMELINE-03 | Phase 6 | Pending |
| REASON-01 | Phase 7 | Pending |
| REASON-02 | Phase 7 | Pending |
| REASON-03 | Phase 7 | Pending |
| REASON-04 | Phase 7 | Pending |
| REASON-05 | Phase 7 | Pending |
| REASON-06 | Phase 7 | Pending |
| SEC-01 | Phase 8 | Pending |
| SEC-02 | Phase 8 | Pending |
| SEC-03 | Phase 8 | Pending |

**Coverage:**
- v1 requirements: 29 total
- Mapped to phases: 29
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-04*
*Last updated: 2026-04-04 after initial definition*
