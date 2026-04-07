---
phase: 04-hybrid-search-index
plan: "02"
subsystem: search
tags: [pgvector, supabase, hybrid-search, rrf, sql-migration]
dependency_graph:
  requires: []
  provides: [search_index table, hybrid_search RPC, fts_search RPC, supabase-backed search.py]
  affects: [backend/services/azure/search.py, backend/scripts/migrations/001_create_search_index.sql]
tech_stack:
  added: [pgvector, supabase-py (rpc calls)]
  patterns: [lazy singleton client, RRF fusion (vector + BM25), upsert pattern]
key_files:
  created:
    - backend/scripts/migrations/001_create_search_index.sql
    - backend/scripts/setup_search_index.py
  modified:
    - backend/services/azure/search.py
decisions:
  - content_vector excluded from upsert row when None — pgvector rejects null vector serialization
  - fts_search RPC added as fallback when no query_vector provided — single SQL path for both modes
  - Mock branch left unchanged — all existing tests continue to pass with USE_MOCK_AZURE=true
  - search() signature extended with optional query_vector param — backward-compatible, all callers unaffected
metrics:
  duration: "5 min"
  completed: "2026-04-07"
  tasks_completed: 2
  files_changed: 3
---

# Phase 04 Plan 02: Supabase pgvector Search Index Summary

Replaced Azure AI Search backend with Supabase pgvector — SQL migration creates `search_index` table and `hybrid_search`/`fts_search` RPCs; `search.py` production branch rewired to Supabase with RRF hybrid retrieval.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | SQL migration — search_index table + hybrid_search function | 159ac18 | backend/scripts/migrations/001_create_search_index.sql, backend/scripts/setup_search_index.py |
| 2 | Rewrite search.py production branch for Supabase pgvector | 68d488a | backend/services/azure/search.py |

## What Was Built

### SQL Migration (`001_create_search_index.sql`)

- `search_index` table with `content_vector vector(1536)` plus text fields for content, source, entities, document metadata
- Three indexes: `user_id` B-tree for filtering, IVFFlat for cosine similarity, GIN for Portuguese FTS
- `hybrid_search()` RPC: Reciprocal Rank Fusion of vector similarity and full-text search (top 20 from each, fused with `1/(rrf_k + rank)` formula)
- `fts_search()` RPC: Portuguese full-text fallback when no embedding provided

### Setup Helper (`setup_search_index.py`)

CLI with two modes:
- `--print-sql`: prints migration to stdout for pasting into Supabase SQL Editor
- `--check`: connects to Supabase and verifies `search_index` table exists

### search.py Rewrite (production branch)

- `_get_supabase_client()` lazy singleton using `SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY`
- `index_document()`: upserts row into `search_index`; omits `content_vector` from row when `None` (avoids pgvector serialization error)
- `search()`: calls `hybrid_search` RPC when `query_vector` provided, falls back to `fts_search` without
- `IndexedDocument` dataclass extended with `content_vector`, `document_family`, `collection_date`, `document_subtype`
- All new params default to `None` — existing callers (`indexer.py`) unaffected
- Mock branch and `_mock_search()` completely unchanged

## Verification

```
cd backend && python -c "from services.azure.search import index_document, search, IndexedDocument; print('ok')"
# -> ok

cd backend && python -c "import scripts.setup_search_index; print('ok')"
# -> ok

grep "azure.search.documents" backend/services/azure/search.py
# -> (no output — Azure SDK removed)
```

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — migration SQL is complete and ready to run. Production branch fully wired to Supabase. Table will not exist until migration is applied in Supabase SQL Editor (intentional — requires human action documented in setup_search_index.py).

## Self-Check: PASSED

- `backend/scripts/migrations/001_create_search_index.sql` — exists
- `backend/scripts/setup_search_index.py` — exists
- `backend/services/azure/search.py` — modified
- Commit `159ac18` — exists
- Commit `68d488a` — exists
