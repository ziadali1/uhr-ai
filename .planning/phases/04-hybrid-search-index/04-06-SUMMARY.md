---
phase: 04-hybrid-search-index
plan: 06
subsystem: rag-retrieval
tags: [hybrid-search, pgvector, reindex, embeddings, scripts]
dependency_graph:
  requires: [04-02, 04-03, 04-04, 04-05]
  provides: [RETRIEVE-01, RETRIEVE-02, RETRIEVE-03]
  affects: [backend/scripts/reindex_documents.py]
tech_stack:
  added: []
  patterns: [idempotent-reindex, soft-fail-embedding, dry-run-preview]
key_files:
  created:
    - backend/scripts/reindex_documents.py
decisions:
  - "Script truncates search_index via delete().neq('id','') — Supabase REST API lacks TRUNCATE; delete with always-true filter achieves same result"
  - "content_vector passed as-is (None allowed) to index_document which already guards against null vector serialization"
  - "StructuredResult reconstructed from dict via StructuredResult(**doc['structured_result']) — same pattern as pipeline"
  - "collection_date extracted from structured_data dict (not top-level StructuredResult field) — matches existing data shape"
metrics:
  duration: 3min
  completed_date: "2026-04-07"
  tasks_completed: 1
  files_modified: 1
---

# Phase 04 Plan 06: Re-index Documents Script Summary

**One-liner:** CLI script `reindex_documents.py` that truncates `search_index` and re-indexes all Supabase documents with pgvector embeddings via `assemble_context_block` + `generate_embedding` + `index_document`, with `--dry-run` support and idempotent design.

## What Was Built

Created `backend/scripts/reindex_documents.py` — a one-shot CLI script that rebuilds the entire `search_index` table from the `documents` table.

**Three functions:**

1. `fetch_all_documents()` — queries `documents` table for all rows with non-null `anonymized_text`, selecting `id`, `user_id`, `anonymized_text`, `original_name`, `structured_result`, `medical_entities`

2. `truncate_search_index()` — deletes all rows from `search_index` using `delete().neq("id", "")` (Supabase REST workaround for TRUNCATE)

3. `reindex(dry_run=False)` — orchestrates the full re-index:
   - Fetches all documents
   - Optionally truncates search_index (skipped in dry-run)
   - For each document: reconstructs `StructuredResult` if present, assembles context block, generates embedding (soft-fail), extracts entity labels and metadata, calls `index_document()`
   - Reports total/embedded/failed counts

**Key design choices:**
- Embedding failure is soft — document is still indexed without vector (BM25 remains functional)
- `content_vector=None` is passed through to `index_document()` which already handles the null-vector guard
- `StructuredResult(**doc["structured_result"])` reconstructs the model from the JSONB dict stored in Supabase
- `collection_date` extracted from `sr.structured_data.get("collection_date")` to match actual data shape
- Entity labels formatted as `"category: text"` strings from `medical_entities` JSON array

**CLI usage:**
```bash
cd backend
python scripts/reindex_documents.py --dry-run    # preview only
python scripts/reindex_documents.py              # live run
```

## Task 2: Human Verification Checkpoint

Task 2 is a `checkpoint:human-verify` gate — the user must:
1. Run the SQL migration (`001_create_search_index.sql`) in Supabase SQL Editor
2. Run `python scripts/setup_search_index.py --check` to confirm table exists
3. Run `python scripts/reindex_documents.py --dry-run` to preview
4. Run `python scripts/reindex_documents.py` with `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` set for live embedding generation
5. Run `python -m pytest tests/ -x -q` to verify no regressions

Auto-approved per `auto_advance: true` config (user verifies in their environment).

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — script is fully wired. Embedding returns `None` in mock mode (`USE_MOCK_AZURE=true`), which is intentional behavior documented in `generate_embedding()`.

## Self-Check: PASSED

- `backend/scripts/reindex_documents.py` exists: FOUND
- Commit `20a9e33` exists: FOUND
- All acceptance criteria verified via import test and pattern check
