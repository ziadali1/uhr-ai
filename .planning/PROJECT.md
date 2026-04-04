# UHR — Unified Health Record

## What This Is

UHR is a personal clinical intelligence system that centralizes a patient's medical history from uploaded documents and makes it queryable, analyzable, and reasoned over by an AI. It ingests medical PDFs and images, extracts structured clinical data, builds a longitudinal patient profile, and supports complex health queries and clinical reasoning — acting as a clinical copilot, not a replacement for a doctor.

## Core Value

A patient's complete medical history — reliably extracted, reliably retrievable, and intelligently reasoned over.

## Requirements

### Validated

- ✓ Document upload (PDF, JPEG, PNG, TIFF, WebP) — existing
- ✓ OCR-based text extraction via Azure Document Intelligence — existing
- ✓ Document classification into families (lab, imaging, clinical, medication, unknown) — existing
- ✓ Structured data extraction via LLM (Claude) per document family — existing
- ✓ RAG indexing in Azure AI Search after upload — existing
- ✓ Chat agent with document retrieval (top-k, SSE streaming) — existing
- ✓ Manual health profile entries (medications, allergies, complaints) — existing
- ✓ Emergency QR profile (medications, allergies, complaints accessible by UUID) — existing
- ✓ Supabase persistence for documents and health data — existing
- ✓ Supabase auth (JWT) with mock bypass for local dev — existing

### Active

**Milestone 1 — Ingestion Foundation (current focus)**

- [ ] Adaptive text extraction: detect native-text PDFs and extract natively before falling back to OCR
- [ ] Multi-version text storage: store native, OCR, and selected-best versions with quality scores
- [ ] Extraction quality scoring: deterministic signal (character density, symbol ratio, line structure)
- [ ] Processing diagnostics: trace how each document was processed (method used, confidence, version selected)
- [ ] Cleaner, higher-quality clinical text indexed into RAG — replacing the current OCR-degraded content

**Milestone 2 — Structured Data Foundation**

- [ ] Longitudinal patient profile: aggregate structured data (labs, diagnoses, medications, symptoms) across documents over time
- [ ] Cross-document entity linking: same lab test, same medication, same condition across multiple documents
- [ ] Structured storage layer: a queryable patient timeline in Supabase, not just document blobs

**Milestone 3 — Clinical Intelligence**

- [ ] Complex query support: trends over time, value ranges, comparisons across visits
- [ ] Clinical reasoning: case summary, relevant findings, differential diagnosis suggestions with evidence and uncertainty
- [ ] Hybrid retrieval: structured + semantic search combined for chat agent responses

### Out of Scope

- ML model training or fine-tuning — prefer deterministic logic and existing LLM APIs
- Replacing doctors or generating clinical decisions without uncertainty — this is a copilot, not a diagnostician
- Multi-user / shared records — single patient, single user scope
- Real-time monitoring or device integration — document-based only
- Billing, scheduling, or EHR integration — not a practice management tool

## Context

**Current state (brownfield):**
- FastAPI backend (Python) + Next.js 14 frontend (TypeScript, static export)
- Azure services: Document Intelligence (OCR), AI Search (RAG), Blob Storage, Text Analytics, OpenAI-compatible LLM endpoint
- Anthropic Claude as LLM for structured extraction and chat
- Supabase for auth + database
- Deployed: backend as Azure Functions, frontend as Azure Static Web Apps

**Critical known issues (from codebase audit):**
- Pipeline always runs OCR even for native-text PDFs — degrades text quality significantly
- RAG uses basic keyword/full-text search only — retrieval fails on many valid queries
- Anonymizer pipeline exists but is never called during upload — PII stored in plaintext
- Emergency profile endpoint (`GET /emergency/{user_id}`) has no auth — exposes full PHI
- `USE_MOCK_AZURE=true` is the default — bypasses all auth if misconfigured in production
- Zero automated tests despite test infrastructure declared in requirements.txt
- No retry logic on any Azure service call

**Architecture decisions already made:**
- Document families: structured_lab, imaging_narrative, clinical_narrative, medication_document, unknown
- Pipeline stages: OCR → classify → clean → extract → entity-build → RAG index → Supabase persist
- Pydantic models for all request/response schemas
- Per-domain FastAPI routers registered in main.py

## Constraints

- **Tech Stack**: Keep FastAPI + Azure + Supabase — no rewrites of the core architecture
- **ML**: No custom model training — use Azure APIs and Anthropic Claude only
- **Compatibility**: Maintain backward compatibility with existing stored documents during evolution
- **Determinism**: Prefer deterministic logic over probabilistic for extraction quality decisions
- **Phasing**: Build in phases — each milestone must be independently shippable

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Adaptive extraction before retrieval improvements | Garbage in = garbage out; fixing extraction quality unblocks everything downstream | — Pending |
| Store multiple text versions (native + OCR + selected) | Enables quality comparison, debugging, and future re-processing without re-uploading | — Pending |
| Quality scoring via deterministic signals | Avoids LLM cost per document just to score quality; character density and symbol ratio are reliable proxies | — Pending |
| Longitudinal profile before clinical reasoning | Clinical reasoning requires reliable structured data across time; must build the data layer first | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-04 after initialization*
