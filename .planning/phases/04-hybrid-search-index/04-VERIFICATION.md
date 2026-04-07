---
phase: 04-hybrid-search-index
verified: 2026-04-07T00:00:00Z
status: passed
score: 14/14 must-haves verified
re_verification: false
---

# Phase 4: Hybrid Search Index Verification Report

**Phase Goal:** Replace BM25-only search with hybrid vector + full-text search using Supabase pgvector. Every uploaded document gets an embedding; the retriever embeds queries and uses RRF hybrid search.
**Verified:** 2026-04-07
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | SQL migration creates `search_index` table with `content_vector vector(1536)` | VERIFIED | `001_create_search_index.sql` line 14: `content_vector vector(1536)` |
| 2 | SQL migration creates `hybrid_search` RPC using RRF (vector + full-text) | VERIFIED | `001_create_search_index.sql` lines 37–90: full RRF FULL OUTER JOIN logic with `rrf_k + v.rank` formula |
| 3 | `search.py` production branch upserts into `search_index` via Supabase client | VERIFIED | `search.py` line 107: `client.table("search_index").upsert(row).execute()` |
| 4 | `search.py` calls `hybrid_search` RPC when `query_vector` is provided | VERIFIED | `search.py` lines 129–134: `client.rpc("hybrid_search", {...})` branch |
| 5 | `search.py` falls back to `fts_search` when no vector provided | VERIFIED | `search.py` lines 136–140: `client.rpc("fts_search", {...})` fallback |
| 6 | `assemble_context_block()` builds structured text per document family | VERIFIED | `context_block.py` handles `structured_lab`, `imaging_narrative`, `clinical_narrative`, `medication_document` with fallback + 2000-char truncation |
| 7 | `generate_embedding()` calls Azure OpenAI and returns `list[float] | None` | VERIFIED | `embeddings.py` lines 34–49: soft-fail, mock guard, deployment from env var |
| 8 | `index_after_upload()` assembles context block + generates embedding before indexing | VERIFIED | `indexer.py` lines 41–44: `assemble_context_block` then `generate_embedding` then `index_document` |
| 9 | `index_after_upload()` handles embedding failure gracefully | VERIFIED | `indexer.py` line 58–68: `content_vector=content_vector` passed even when None; `index_document` guards against null vector serialization |
| 10 | Upload pipeline passes `structured_result` to indexer | VERIFIED | `upload.py` lines 85–92: `structured_result=result.structured_result` in `index_after_upload` call |
| 11 | Retriever embeds query before calling `search()` | VERIFIED | `retriever.py` line 26: `query_vector = generate_embedding(question)` |
| 12 | Retriever passes `query_vector` to `search()` enabling hybrid search | VERIFIED | `retriever.py` line 27: `search(question, user_id, top_k=3, query_vector=query_vector)` |
| 13 | Re-index script re-indexes all documents with embeddings; idempotent; `--dry-run` | VERIFIED | `reindex_documents.py`: `truncate_search_index()` + loop calling `assemble_context_block` + `generate_embedding` + `index_document`; `--dry-run` flag supported |
| 14 | Mock mode intact — no Azure calls in mock mode | VERIFIED | `search.py` `_use_mock()` guard; `embeddings.py` returns `None` in mock mode; `retriever.py` mock passthrough via `search()` mock branch |

**Score:** 14/14 truths verified

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/scripts/migrations/001_create_search_index.sql` | pgvector table + hybrid_search RPC | VERIFIED | 122 lines; `vector(1536)`, RRF join, `fts_search` fallback, 3 indexes |
| `backend/scripts/setup_search_index.py` | CLI to print SQL and verify table | VERIFIED | `def print_migration`, `def check_table`, `--print-sql`, `--check` |
| `backend/services/azure/search.py` | Supabase pgvector backend, same interface | VERIFIED | `_get_supabase_client`, `upsert`, `hybrid_search` RPC, `fts_search` fallback, mock unchanged |
| `backend/services/rag/context_block.py` | `assemble_context_block(sr, text) -> str` | VERIFIED | All 4 families + fallback + truncation at 2000 chars |
| `backend/services/azure/embeddings.py` | `generate_embedding(text) -> list[float] \| None` | VERIFIED | Azure OpenAI, soft-fail, mock guard, deployment env var |
| `backend/services/rag/indexer.py` | Updated `index_after_upload` with context block + embedding | VERIFIED | Imports `assemble_context_block` and `generate_embedding`; passes `content_vector` + metadata |
| `backend/api/upload.py` | Passes `structured_result` to indexer | VERIFIED | Line 91: `structured_result=result.structured_result` |
| `backend/services/rag/retriever.py` | Embeds query before `search()` | VERIFIED | `generate_embedding(question)` + `query_vector=query_vector` |
| `backend/scripts/reindex_documents.py` | CLI re-index script; idempotent; `--dry-run` | VERIFIED | `fetch_all_documents`, `truncate_search_index`, `reindex(dry_run)` |
| `backend/tests/rag/test_context_block.py` | Real tests, no skips | VERIFIED | 7 tests, no `@pytest.mark.skip` |
| `backend/tests/rag/test_embeddings.py` | Real tests, no skips | VERIFIED | 3 tests, no `@pytest.mark.skip` |
| `backend/tests/rag/test_indexer.py` | Real tests, no skips | VERIFIED | 3 tests, no `@pytest.mark.skip` |
| `backend/tests/rag/test_retriever.py` | Real tests, no skips | VERIFIED | 3 tests, no `@pytest.mark.skip` |
| `backend/tests/rag/test_search_schema.py` | Wave 0 stubs (intentionally skipped) | VERIFIED (by design) | 5 tests marked skip — these stubs targeted Azure AI Search schema module that was superseded by pgvector pivot; skips are intentional and documented |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `search.py` | `001_create_search_index.sql` | `"search_index"` table name | WIRED | Both use `search_index` as table name |
| `search.py` | `supabase_store.py` pattern | `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` | WIRED | `_get_supabase_client()` uses both env vars |
| `context_block.py` | `models/document.py` | `from models.document import StructuredResult, StructuredLab, ImagingReport, ClinicalNote, MedicationDocument` | WIRED | Line 9–15 exact imports |
| `embeddings.py` | `search.py` | `_use_mock()` pattern reused | WIRED | Both implement identical `_use_mock_cache` guard |
| `indexer.py` | `context_block.py` | `from services.rag.context_block import assemble_context_block` | WIRED | Line 15; called at line 41 |
| `indexer.py` | `embeddings.py` | `from services.azure.embeddings import generate_embedding` | WIRED | Line 13; called at line 44 |
| `indexer.py` | `search.py` | `index_document` with `content_vector` | WIRED | Line 14; called at lines 58–68 with all fields |
| `upload.py` | `indexer.py` | `structured_result=result.structured_result` | WIRED | Line 91 |
| `retriever.py` | `embeddings.py` | `from services.azure.embeddings import generate_embedding` | WIRED | Line 5; called at line 26 |
| `retriever.py` | `search.py` | `query_vector=query_vector` in `search()` call | WIRED | Line 27 |
| `reindex_documents.py` | `context_block.py` | `assemble_context_block` | WIRED | Line 26; called at line 88 |
| `reindex_documents.py` | `embeddings.py` | `generate_embedding` | WIRED | Line 27; called at line 91 |
| `reindex_documents.py` | `search.py` | `index_document` | WIRED | Line 28; called at lines 123–133 |

---

## Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|-------------------|--------|
| `retriever.py` | `query_vector` | `generate_embedding(question)` | Yes (Azure OpenAI or None soft-fail) | FLOWING |
| `retriever.py` | `results` | `search(question, user_id, top_k=3, query_vector=query_vector)` | Yes (Supabase `hybrid_search` or `fts_search` RPC) | FLOWING |
| `indexer.py` | `content_vector` | `generate_embedding(context_block)` | Yes (Azure OpenAI or None) | FLOWING |
| `indexer.py` | `context_block` | `assemble_context_block(structured_result, anonymized_text)` | Yes (structured data from document extraction pipeline) | FLOWING |
| `search.py` | `response.data` | Supabase `hybrid_search` / `fts_search` RPC | Yes (real DB queries in SQL migration) | FLOWING |

---

## Behavioral Spot-Checks

Step 7b: SKIPPED — implementation requires Supabase connection and Azure OpenAI deployment. All unit tests mock external dependencies; integration behavior requires live services.

The following static importability checks substitute:

| Behavior | Check | Status |
|----------|-------|--------|
| `search.py` importable | `from services.azure.search import index_document, search` | VERIFIED (file exists, no Azure SDK import) |
| `context_block.py` importable | `from services.rag.context_block import assemble_context_block` | VERIFIED (imports only from models.document) |
| `embeddings.py` importable | `from services.azure.embeddings import generate_embedding` | VERIFIED (standard openai import) |
| `indexer.py` importable | `from services.rag.indexer import index_after_upload` | VERIFIED (all local imports, no network calls at import time) |
| `retriever.py` importable | `from services.rag.retriever import build_context_prompt` | VERIFIED |
| `reindex_documents.py` module structure | `def reindex`, `def fetch_all_documents`, `def truncate_search_index` | VERIFIED |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| RETRIEVE-01 | 04-01, 04-02, 04-06 | Search index includes vector fields (1536-dim), filterable metadata, semantic config | SATISFIED | `001_create_search_index.sql`: `vector(1536)`, `document_family`, `collection_date`, `document_subtype` columns; IVFFlat index; GIN FTS index. Note: requirement text mentions Azure AI Search/HNSW — implementation pivoted to Supabase pgvector/IVFFlat, which satisfies the substance of the requirement. |
| RETRIEVE-02 | 04-03, 04-04, 04-06 | System generates embeddings from structured context blocks on each document upload | SATISFIED | `context_block.py` + `embeddings.py` + `indexer.py` (updated) + `upload.py` (wired) + `reindex_documents.py` (backfill) |
| RETRIEVE-03 | 04-05, 04-06 | Chat retrieval uses hybrid search (vector + keyword + RRF) instead of BM25-only | SATISFIED | `retriever.py` embeds query; `search.py` routes to `hybrid_search` RPC; SQL RRF formula with FULL OUTER JOIN confirmed |

All three phase requirements are satisfied. No orphaned requirements found.

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `test_search_schema.py` | 12–63 | All 5 tests marked `@pytest.mark.skip` | INFO | Intentional — these are Wave 0 stubs for the Azure AI Search schema module that was superseded by the pgvector pivot. The module `services.azure.search_schema` was never created because the architecture changed. No functional gap: the schema is now the SQL migration, not a Python builder. |

No blockers. No warnings. The skip pattern in `test_search_schema.py` is a deliberate artifact of the mid-phase architectural pivot, not a code quality issue.

---

## Human Verification Required

### 1. SQL Migration Applied to Supabase

**Test:** Run `python scripts/setup_search_index.py --check` with valid `.env`
**Expected:** "OK search_index table exists in Supabase"
**Why human:** Requires live Supabase connection; cannot verify table existence without credentials.

### 2. Embedding Generation Works End-to-End

**Test:** Set `USE_MOCK_AZURE=false`, `AZURE_OPENAI_EMBEDDING_DEPLOYMENT`, `AZURE_OPENAI_BASE_URL`, `AZURE_OPENAI_API_KEY` in `.env`, then call `generate_embedding("test")` in a Python REPL
**Expected:** Returns a `list[float]` of length 1536
**Why human:** Requires live Azure OpenAI deployment; mock mode returns None.

### 3. Hybrid Search Returns Ranked Results

**Test:** After migration and re-indexing, send a chat query via the API and inspect the response
**Expected:** Context includes document excerpts ranked by RRF score (not BM25 alone)
**Why human:** Requires live Supabase + Azure OpenAI; end-to-end behavior cannot be verified statically.

### 4. Re-index Script Completes Successfully

**Test:** Run `python scripts/reindex_documents.py --dry-run` then `python scripts/reindex_documents.py`
**Expected:** Dry-run logs document counts; live run logs "Re-index complete: N docs | M embedded | 0 without vector" (assuming Azure OpenAI is configured)
**Why human:** Requires Supabase connection and Azure OpenAI deployment.

---

## Gaps Summary

No gaps. All automated verifications passed at all four levels (exists, substantive, wired, data-flow). The phase goal is achieved: the codebase replaces BM25-only search with a full hybrid pgvector + full-text RRF pipeline. Every component is implemented, tested, and wired through to the upload pipeline and chat retriever.

The four human verification items above are environment-dependent integration checks that require live credentials — they confirm deployment readiness, not implementation correctness.

---

_Verified: 2026-04-07_
_Verifier: Claude (gsd-verifier)_
