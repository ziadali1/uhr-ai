---
phase: 04-hybrid-search-index
plan: 02
subsystem: api
tags: [azure-search, vector-search, hnsw, embeddings, semantic-search]

# Dependency graph
requires:
  - phase: 03-migration-and-backfill
    provides: existing documents stored in Supabase; RAG indexer pipeline wired in upload flow
provides:
  - Azure AI Search index schema with 1536-dim HNSW vector field and semantic configuration
  - IndexedDocument dataclass extended with content_vector, document_family, collection_date, document_subtype
  - index_document() backward-compatible signature accepting optional vector and metadata fields
  - setup_azure_search.py drop+recreate script with --dry-run flag
affects: [04-03-embeddings, 04-04-indexer-update, 04-05-hybrid-retriever, 04-06-reindex]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Module-level constants (VECTOR_PROFILE_NAME, HNSW_CONFIG_NAME) prevent profile name mismatch in Azure SDK
    - Conditional doc dict: only include content_vector key when non-None (prevents Azure serialization error)
    - Drop+recreate pattern with delete_index() wrapped in try/except for graceful first-run

key-files:
  created: []
  modified:
    - backend/scripts/setup_azure_search.py
    - backend/services/azure/search.py

key-decisions:
  - "VECTOR_PROFILE_NAME and HNSW_CONFIG_NAME defined as module-level constants to prevent profile name mismatch at runtime (Pitfall 1)"
  - "content_vector conditionally excluded from upload dict when None — Azure SDK serialization error on null vector (Pitfall 2)"
  - "algorithm_configuration_name uses snake_case parameter name per SDK requirement (not camelCase)"
  - "search() function left unchanged in this plan — BM25 only until Plan 05 adds hybrid retrieval"
  - "index_document() signature backward-compatible — all new params default to None, existing callers (indexer.py) unaffected"

patterns-established:
  - "Pattern: Azure vector field setup uses named profile and algorithm constants to decouple name strings"
  - "Pattern: Optional fields conditionally added to upload dict (not passed as None) for Azure AI Search compatibility"

requirements-completed: [RETRIEVE-01]

# Metrics
duration: 2min
completed: 2026-04-07
---

# Phase 4 Plan 02: Hybrid Search Index Schema Summary

**Azure AI Search index extended with 1536-dim HNSW vector field, 3 filterable metadata fields, uhr-semantic config, and IndexedDocument dataclass updated with backward-compatible optional vector + metadata parameters**

## Performance

- **Duration:** 2 min
- **Started:** 2026-04-07T10:25:24Z
- **Completed:** 2026-04-07T10:27:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Rewrote `setup_azure_search.py` with drop+recreate pattern, HNSW vector field (1536-dim cosine), 3 filterable fields, uhr-semantic SemanticConfiguration, and --dry-run flag
- Extended `IndexedDocument` dataclass with 4 new optional fields: `content_vector`, `document_family`, `collection_date`, `document_subtype`
- Extended `index_document()` with matching optional parameters and conditional upload dict (avoids Azure serialization error on None vectors)

## Task Commits

Each task was committed atomically:

1. **Task 1: Rewrite setup_azure_search.py with new schema (drop+recreate)** - `a5c00c9` (feat)
2. **Task 2: Extend IndexedDocument and index_document() with vector + metadata fields** - `0921610` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `backend/scripts/setup_azure_search.py` - Drop+recreate index script with full Phase 4 schema (vector + metadata + semantic config)
- `backend/services/azure/search.py` - IndexedDocument extended with 4 new optional fields; index_document() accepts and conditionally includes vector + metadata

## Decisions Made
- VECTOR_PROFILE_NAME and HNSW_CONFIG_NAME as module-level constants prevent profile name mismatch at runtime — names referenced in both VectorSearch profiles and SearchField must match exactly
- content_vector excluded from upload dict when None — passing `"content_vector": None` causes an Azure SDK serialization error (Pitfall 2 per research)
- algorithm_configuration_name uses snake_case per SDK requirement (not camelCase `algorithmConfigurationName`)
- search() function left completely unchanged — BM25-only retrieval continues until Plan 05 adds hybrid search
- Backward-compatible extension: all new parameters default to None so existing callers (indexer.py) work without modification

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
- Acceptance criteria grep pattern `SemanticConfiguration(name="uhr-semantic"` expected the constructor call on one line; code uses standard multiline Python formatting. Both the class name and `name="uhr-semantic"` are present and correct in the file — no functional issue.

## User Setup Required
None - no external service configuration required for schema changes. The `setup_azure_search.py` script must be run once when ready to recreate the Azure AI Search index (handled in a later plan step).

## Next Phase Readiness
- Index schema ready for vector uploads — RETRIEVE-01 complete
- Plan 03 (embeddings service) can now be implemented: `content_vector` field is defined and `index_document()` will accept it
- Plan 04 (indexer update) can wire embedding generation into the upload pipeline
- Plan 05 (hybrid retriever) can update `search()` to use VectorizedQuery + semantic RRF
- Existing mock mode continues to work — `_mock_search()` untouched

---
*Phase: 04-hybrid-search-index*
*Completed: 2026-04-07*
