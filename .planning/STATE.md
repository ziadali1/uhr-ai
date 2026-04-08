---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
current_plan: 1
status: Executing Phase 06
stopped_at: Completed 06-02-PLAN.md
last_updated: "2026-04-08T19:16:46.067Z"
progress:
  total_phases: 8
  completed_phases: 5
  total_plans: 25
  completed_plans: 24
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-04)

**Core value:** A patient's complete medical history — reliably extracted, reliably retrievable, and intelligently reasoned over.
**Current focus:** Phase 06 — patient-timeline-api-and-dashboard

## Current Phase

**Phase 3: Migration and Backfill** — In progress (2/3 plans done)

Current Plan: 1
Last completed: 03-01 + 03-02 (Wave 1 — both migration scripts built and tested)

## Milestone

**Milestone 1 — Ingestion Foundation** (Phases 1–3)

## Phase History

| Phase | Status | Completed |
|-------|--------|-----------|
| 01-adaptive-text-extraction | Complete | 2026-04-05 |
| 02-longitudinal-patient-data-model | Complete | 2026-04-06 |

## Decisions

| Phase | Decision |
|-------|----------|
| 01-01 | Return plain dict from is_native_page() to prevent circular imports with orchestrator |
| 01-01 | Font reality checked via GlyphLessFont name blocklist AND size-0 span filter |
| 01-01 | Three-signal classifier: char>=50, image_coverage<0.60, has_real_fonts |
| 01-02 | Line length signal gates on printable-char presence to avoid false positives on pure garbage blobs |
| 01-02 | fitz imported at module level in extractor.py; is_native_page imported via services.extraction.classifier |

- [Phase 01-03]: OCR callable injected into router as argument to prevent circular import between document_intelligence and router
- [Phase 01-03]: extract_text_with_meta() added as metadata-rich variant for Plan 4 to use when persisting extraction results
- [Phase 01-04]: Pipeline orchestrator updated to use extract_text_with_meta() to avoid double extraction; exposes extraction_result in PipelineResult
- [Phase 01-04]: supabase_store text_extraction_meta INSERT wrapped in try/except pending Supabase migration
- [Phase 01-05]: fitz imported at module level in router.py to support unittest.mock patching
- [Phase 01-05]: PasswordProtectedError raises HTTP 422 with Portuguese message; caught before generic Exception handler in upload.py
- [Phase 02-01]: patient_observations uses non-unique index idx_obs_dedup (not a UNIQUE constraint) to allow storing both conflicting rows per D-01; application code in patient_store.py handles conflict detection
- [Phase 02-01]: analyte_aliases seeded with 25 rows including both accented and unaccented Brazilian lab term variants for robust alias lookup
- [Phase 02-01]: user_id stored as TEXT across all patient tables to match existing documents table pattern
- [Phase 02-02]: Observation pre-check uses SELECT then conditional INSERT (not upsert) so both conflicting rows coexist per D-01
- [Phase 02-02]: _load_aliases wrapped in try/except returning {} for graceful degradation in dev without analyte_aliases table
- [Phase 02-02]: Brazilian date falls back to upload_date (not None) to ensure concrete observed_date for dedup key — NULL != NULL in SQL
- [Phase 02-03]: Double try/except for promotion (outer in upload.py + inner in patient_store.py) is intentional defense-in-depth per D-07: upload always succeeds even if promotion has bugs
- [Phase 03-01]: Direct health_entries table query (not health_store.list_by_user) to include active=False entries — zero data loss
- [Phase 03-01]: document_id=None for all manual entry migrations — no source document; started_at/ended_at dropped as patient_medications has no date-range columns
- [Phase 03-02]: Backfill script is intentionally thin — delegates all logic to list_by_user() and promote_to_patient_tables() without reimplementation
- [Phase 03-02]: Error counting per-doc so one failure does not abort the entire backfill; dry_run increments promoted counter for preview accuracy
- [Phase 03-03]: User-id auto-discovered from health_entries table using service role key — no need to ask user for UUID
- [Phase 03-03]: patient_observations=0 is correct — all 3 structured_lab docs had empty observations[] arrays due to pre-Phase-1 OCR degradation; not a migration bug
- [Phase 04-03]: conftest.py added at backend/ root for pytest sys.path setup
- [Phase 04-03]: test files for context_block and embeddings created from scratch — no pre-existing Wave 0 stubs found
- [Phase 04-02]: VECTOR_PROFILE_NAME and HNSW_CONFIG_NAME as module-level constants prevent profile name mismatch at runtime (Pitfall 1)
- [Phase 04-02]: content_vector excluded from upload dict when None — Azure SDK serialization error on null vector (Pitfall 2)
- [Phase 04-02]: search() function unchanged — BM25-only until Plan 05 adds hybrid retrieval
- [Phase 04-02]: index_document() backward-compatible — all new params default None, existing callers (indexer.py) unaffected
- [Phase 04-01]: All Wave 0 stubs use @pytest.mark.skip (not xfail) — skip is cleaner for Wave 0 where the module under test does not yet exist
- [Phase 04-01]: Imports placed inside Wave 0 test bodies — prevents ImportError from blocking pytest collection when modules do not yet exist
- [Phase 04-02]: content_vector excluded from upsert row when None — pgvector rejects null vector serialization
- [Phase 04-02]: fts_search RPC added as fallback when no query_vector provided — single SQL code path for both modes
- [Phase 04-02]: search() signature extended with optional query_vector param — backward-compatible, all existing callers unaffected
- [Phase 04-05]: query_vector always passed to search() — None triggers fts_search fallback, non-None triggers hybrid_search RPC
- [Phase 04-04]: structured_result defaults to None in index_after_upload — backward-compatible with all existing callers
- [Phase 04-04]: collection_date extracted from structured_data dict, not top-level StructuredResult field — matches existing data shape
- [Phase 04-06]: Script truncates search_index via delete().neq('id','') — Supabase REST lacks TRUNCATE
- [Phase 04-06]: content_vector passed as-is (None) to index_document which already guards against null vector serialization
- [Phase 05-01]: import pytest added to test_retriever.py (was missing before adding skip decorator)
- [Phase 05-02]: Mock guard in route_query() returns search_only immediately — avoids RoutingResult validation failure on '{}' from generate_json() in mock mode (Pitfall 2)
- [Phase 05-02]: time_range typed as list[str] | None, NOT tuple[date, date] — Pydantic 2.x JSON serialization compatibility (Pitfall 5)
- [Phase 05-03]: models.document imported directly in router.py — D-10: context_block.py is read-only, not re-used for chat assembler
- [Phase 05-03]: assemble_chat_block uses excerpt[:400] fallback for unknown family and dispatch exceptions — same soft-fail principle as D-04 for route_query
- [Phase 05-04]: Route query before retrieval: route_query() called first before any embedding or SQL — api/chat.py signature unchanged
- [Phase 05-04]: assemble_chat_block called per search result with collection_date=None (SearchResult lacks date; assembler handles gracefully)
- [Phase 05]: patch _use_mock_cache to None before each mock-mode test so _use_mock() re-reads env var (cache invalidation)
- [Phase 05]: test_sql_user_isolation uses select_mock.eq.call_args_list to inspect first .eq() call in chain — method_calls on mock_client only shows top-level calls
- [Phase 06-01]: value_num and ref_low/ref_high are NOT DB columns — derived at query-time from value_str and reference_range in _enrich_observation()
- [Phase 06-01]: date_from/date_to sliced to [:10] chars before Supabase .gte/.lte call per Pitfall 4
- [Phase 06-02]: Emergency soft-fail returns EmergencyProfile with empty lists when _get_client raises — never None on DB error
- [Phase 06-02]: client_failed flag distinguishes DB error from successful-but-empty query for None-return logic

## Performance Metrics

| Phase | Plan | Duration | Tasks | Files |
|-------|------|----------|-------|-------|
| 01 | 01 | 2min | 2 | 6 |
| 01 | 02 | 2min | 2 | 2 |
| 01 | 03 | 2min | 2 | 3 |
| 01 | 04 | 3min | 2 | 5 |
| 01 | 05 | 8min | 2 | 6 |
| 02 | 01 | 4min | 2 | 2 |
| Phase 02 P02 | 5min | 2 tasks | 3 files |
| Phase 02 P03 | 1min | 2 tasks | 1 files |
| 03 | 01 | 2min | 1 | 3 |
| 03 | 02 | 1min | 1 | 3 |
| Phase 03 P03 | 5min | 2 tasks | 0 files |
| Phase 04 P02 | 2min | 2 tasks | 2 files |
| Phase 04 P03 | 2min | 2 tasks | 7 files |
| Phase 04 P01 | 2min | 1 tasks | 7 files |
| Phase 04 P02 | 5min | 2 tasks | 3 files |
| Phase 04 P05 | 68s | 1 tasks | 2 files |
| Phase 04 P04 | 2min | 2 tasks | 3 files |
| Phase 04 P06 | 3min | 1 tasks | 1 files |
| Phase 05 P01 | 5min | 2 tasks | 2 files |
| Phase 05 P02 | 2min | 2 tasks | 1 files |
| Phase 05 P03 | 4min | 1 tasks | 1 files |
| Phase 05 P04 | 8min | 1 tasks | 2 files |
| Phase 05 P05 | 5min | 2 tasks | 2 files |
| Phase 06 P01 | 2min | 2 tasks | 4 files |
| Phase 06 P02 | 5min | 2 tasks | 5 files |

## Last Session

**Stopped at:** Completed 06-02-PLAN.md
**Timestamp:** 2026-04-06T19:00:00Z

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
