# Phase 4: Hybrid Search Index — Context

**Gathered:** 2026-04-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Upgrade Azure AI Search from flat BM25 keyword search to hybrid search: vector similarity + keyword + RRF fusion. This phase ships:
- New index schema (vector field + filterable metadata + semantic config)
- `services/azure/embeddings.py` — embedding generation from structured context blocks
- Updated `services/rag/indexer.py` — generate and store embedding on upload
- Updated `services/rag/retriever.py` — hybrid VectorizedQuery + search_text with RRF
- Re-index script for all existing documents

This phase does NOT include: query intent routing (Phase 5), structured context block assembler for chat (Phase 5), frontend timeline changes (Phase 6). Embedding content is a lightweight version of structured_result — the full assembler is Phase 5's job.

</domain>

<decisions>
## Implementation Decisions

### What Gets Embedded

- **D-01:** Do NOT embed `anonymized_text` (raw OCR output). Embed a lightweight structured context block assembled from `structured_result` fields.
- **D-02:** Context block assembly order (use what's available, skip missing fields):
  1. `summary` — top-level summary field if present
  2. `entities_for_memory` — key clinical entities list if present
  3. Lab findings — for each finding: `"{name}: {value} {unit} [{flag}]"` when `structured_result` is a `StructuredLab`
  4. Imaging impression/findings — `impression` and `findings` fields from `ImagingReport`
  5. Diagnoses, symptoms, allergies, medications — from `ClinicalNote` and `MedicationDocument`
- **D-03:** If `structured_result` is null or missing all fields → fall back to first 1000 chars of `anonymized_text`. Document this fallback in code.
- **D-04:** Block format: compact plain text, fields separated by newlines, no JSON. Max ~500 tokens — truncate if exceeded. No headers or labels needed, just the values.
- **D-05:** This lightweight block is Phase 4's pragmatic approximation. Phase 5 builds the canonical assembler — Phase 4's block will be replaced or extended at that point.

### Embedding Provider

- **D-06:** Use Azure OpenAI embeddings only. No second provider.
- **D-07:** Model: `text-embedding-3-small` (1536-dim output). This matches the `content_vector` field dimension in RETRIEVE-01.
- **D-08:** Deployment name: read from env var `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` (e.g., `text-embedding-3-small`). Endpoint and key reuse existing `AZURE_OPENAI_ENDPOINT` / `AZURE_OPENAI_KEY` env vars if applicable, or add separate vars if the embedding endpoint differs.
- **D-09:** This phase includes provisioning/configuring the Azure embedding deployment if it is not already available. The plan must document what Azure-side setup is required (deployment name, region, quota).
- **D-10:** Embedding generation is a network call — must be wrapped in try/except. Failure logs and skips; does not block upload (soft-fail, same as Phase 2 D-04 pattern).

### Chunking Strategy

- **D-11:** One vector per document. Same index cardinality as current system.
- **D-12:** No passage-level chunking in Phase 4. Chunking is a post-Phase 4 optimization once hybrid retrieval is stable.
- **D-13:** Each index document continues to correspond to one uploaded document (one `doc_id`).

### Re-Index Migration Approach

- **D-14:** Drop + recreate the index. Delete existing index, define new schema, re-index all documents.
- **D-15:** Brief search downtime during migration is acceptable — this is a single-user personal system.
- **D-16:** Re-index script: iterate all documents with non-null `anonymized_text` (or `structured_result`), assemble context block, generate embedding, upload to new index. Must be idempotent (safe to re-run).
- **D-17:** Documents with `document_family = 'unknown'` and null `structured_result` → use anonymized_text fallback (D-03).

### Index Schema

- **D-18:** New fields beyond current `{id, user_id, content, source_name, entities}`:
  - `content_vector` — 1536-dim float32, HNSW algorithm, cosine similarity
  - `document_family` — filterable string (`structured_lab`, `imaging_narrative`, `clinical_narrative`, `medication_document`, `unknown`)
  - `collection_date` — filterable ISO date string (from `structured_result` date fields if available, else null)
  - `document_subtype` — filterable string (optional, null if not determinable)
  - `semantic_configuration` — named config on the index (e.g., `uhr-semantic`) pointing at `content` as the primary content field
- **D-19:** Existing fields `content`, `source_name`, `entities` remain. `content` continues to hold the text used for BM25 keyword search.

### Retriever Hybrid Query

- **D-20:** Replace current `search_text`-only call with: `VectorizedQuery(vector=query_embedding, k_nearest_neighbors=50, fields="content_vector")` + `search_text=query` + `query_type="semantic"` + RRF fusion.
- **D-21:** Top-k remains 3 by default (same as current). Can be tuned later.
- **D-22:** Retriever generates its own embedding for the query text before calling the hybrid search.

### Mock Mode

- **D-23:** Mock mode must continue working. In mock mode: skip embedding generation entirely, use existing keyword mock search logic (`_mock_search`). No vector simulation needed.
- **D-24:** The `USE_MOCK_AZURE` guard already in `search.py` covers this — extend it to the new embeddings service.

### Claude's Discretion

- Internal function signatures for `generate_embedding()` and `assemble_context_block()`
- Whether `embeddings.py` and the context block assembler are in `services/azure/` or a new `services/rag/` file
- Exact env var names for Azure embedding endpoint/key (follow existing naming conventions)
- Error logging format for embedding failures
- Whether the re-index script is a standalone CLI script or a `/admin/reindex` endpoint

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Current search implementation
- `backend/services/azure/search.py` — Full existing search implementation: BM25 only, mock mode, `IndexedDocument` + `SearchResult` dataclasses, `index_document()`, `search()`. This is the file being extended.
- `backend/services/rag/indexer.py` — Current indexer: receives `anonymized_text` + entities, calls `index_document()`
- `backend/services/rag/retriever.py` — Current retriever: pure BM25 `search_text`, builds system prompt

### Data models (source of structured_result fields for context block assembly)
- `backend/models/document.py` — `StructuredLab`, `LabFinding`, `ImagingReport`, `ClinicalNote`, `MedicationDocument`, `StructuredResult` union type — these define what fields are available per document family

### Upload pipeline (where embedding generation will be triggered)
- `backend/api/upload.py` — Pipeline integration point; indexer is called after anonymization

### Requirements for this phase
- `.planning/REQUIREMENTS.md` §Retrieval — RETRIEVE-01, RETRIEVE-02, RETRIEVE-03
- `.planning/ROADMAP.md` §Phase 4 — Done-when criteria and plan breakdown

### Phase 2 context (soft-fail pattern to continue)
- `.planning/phases/02-longitudinal-patient-data-model/02-CONTEXT.md` — D-04 through D-07: soft-fail pattern, idempotency, try/except logging — replicate for embedding generation

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `search.py` → `_use_mock()` singleton pattern: reuse this in `embeddings.py` to gate Azure embedding calls
- `search.py` → `SearchClient` + `AzureKeyCredential` import pattern: same pattern for `SearchIndexClient` (schema management)
- `models/document.py` → `StructuredLab.findings` (list of `LabFinding`), `ImagingReport.impression`, `ClinicalNote.diagnoses/symptoms`, `MedicationDocument.medications` — these are the source fields for D-02

### Established Patterns
- Mock guard: `if _use_mock(): return` before any Azure SDK call
- Module-level singleton for clients (`_client: X | None = None`)
- Soft-fail: `try/except Exception as e: logger.error(...); return` (never raise from optional steps)
- Env var access: `os.environ["KEY"]` for required vars, `os.environ.get("KEY", default)` for optional

### Integration Points
- New: `backend/services/azure/embeddings.py` — `generate_embedding(text: str) -> list[float] | None` (None on failure)
- New: `backend/services/rag/context_block.py` (or inline in indexer) — `assemble_context_block(structured_result, anonymized_text) -> str`
- Modified: `backend/services/azure/search.py` — extend `IndexedDocument` with vector + metadata fields; extend `index_document()` to accept + store vector; update `search()` to hybrid query
- Modified: `backend/services/rag/indexer.py` — assemble context block → generate embedding → pass to `index_document()`
- Modified: `backend/services/rag/retriever.py` — embed query → hybrid search call
- New: re-index script (location TBD by planner)

</code_context>

<specifics>
## Specific Ideas

- **Embedding soft-fail in indexer**: if `generate_embedding()` returns None, call `index_document()` with `vector=None` — document still gets BM25-indexed without a vector. Hybrid query gracefully degrades to BM25-only when vector is missing.
- **Context block max tokens**: ~500 tokens is a guideline. Simple truncation (character limit ~2000 chars) is fine in Phase 4 — no need for token counting libraries.
- **Re-index script idempotency**: since the index is dropped+recreated, re-running the script starts fresh — idempotency comes for free.
- **Azure AI Search tier**: the plan must verify the subscription tier supports vector search (Standard S1 or higher required). If on Basic, upgrade is part of Phase 4's scope.

</specifics>

<deferred>
## Deferred Ideas

- Passage-level chunking — after hybrid retrieval is stable (post-Phase 4)
- Canonical structured context block assembler — Phase 5 (RETRIEVE-05)
- Query intent routing — Phase 5 (RETRIEVE-04)
- Re-ranking with cross-encoder — future milestone
- Multi-vector per document (one per section) — future optimization

</deferred>

---

*Phase: 04-hybrid-search-index*
*Context gathered: 2026-04-06*
