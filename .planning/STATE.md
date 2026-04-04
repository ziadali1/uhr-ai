# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-04)

**Core value:** A patient's complete medical history — reliably extracted, reliably retrievable, and intelligently reasoned over.
**Current focus:** Phase 1 — Adaptive Text Extraction

## Current Phase

**Phase 1: Adaptive Text Extraction** — Not started

Next: `/gsd:plan-phase 1`

## Milestone

**Milestone 1 — Ingestion Foundation** (Phases 1–3)

## Phase History

| Phase | Status | Completed |
|-------|--------|-----------|
| — | — | — |

## Key Context

- Brownfield project: existing FastAPI + Next.js system with OCR pipeline, RAG chat, Supabase storage
- All documents currently extracted via OCR even when native text is available
- 5 new Postgres tables needed before retrieval improvements (Phases 2–3)
- Security issue: emergency endpoint has no auth — Phase 8 addresses this
- Research complete: see `.planning/research/` for extraction, patient-profile, retrieval, clinical-reasoning findings

## Planning Artifacts

- `.planning/PROJECT.md` — project context and requirements evolution
- `.planning/REQUIREMENTS.md` — 29 v1 requirements across 8 phases
- `.planning/ROADMAP.md` — 8-phase roadmap across 3 milestones
- `.planning/research/extraction.md` — PyMuPDF, quality scoring, routing patterns
- `.planning/research/patient-profile.md` — longitudinal schema, dedup strategy
- `.planning/research/retrieval.md` — hybrid search, Azure AI Search capabilities
- `.planning/research/clinical-reasoning.md` — differential generation, safety guardrails
- `.planning/codebase/` — full codebase map (7 documents)
