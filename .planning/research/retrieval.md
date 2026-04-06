# Research: Clinical RAG and Retrieval Patterns

## Current State (Diagnosed)

The current retrieval is **pure BM25 with top-k=3 and 500-char raw text truncation**:
- No vectors, no semantic ranking
- No structured metadata filters
- No temporal query support
- The rich structured data in Supabase (`StructuredLab`, `ImagingReport`, `ClinicalNote`, etc.) is **completely unused** by the retrieval layer
- Context passed to Claude is degraded OCR fragments, not structured findings

## Azure AI Search 11.6.0b4 Capabilities (Verified)

The current SDK version fully supports hybrid search:

| Feature | Available | Notes |
|---------|-----------|-------|
| `VectorizedQuery` class | Yes | Triggers RRF fusion when combined with `search_text` |
| Reciprocal Rank Fusion (RRF) | Yes | Automatic when both vector + keyword queries provided |
| Semantic ranking | Yes | Requires Standard tier; `k_nearest_neighbors=50` |
| Filterable metadata fields | Yes | `document_family`, `collection_date`, `document_subtype` |
| Aggregation / numeric queries | No | Must go to Supabase SQL, not Azure AI Search |

## Index Rebuild Required

The current index must be rebuilt to add:

```python
fields = [
    SimpleField("id", type=SearchFieldDataType.String, key=True),
    SimpleField("user_id", type=SearchFieldDataType.String, filterable=True),
    SimpleField("document_id", type=SearchFieldDataType.String, filterable=True),
    SimpleField("document_family", type=SearchFieldDataType.String, filterable=True),
    SimpleField("document_subtype", type=SearchFieldDataType.String, filterable=True),
    SimpleField("collection_date", type=SearchFieldDataType.DateTimeOffset,
                filterable=True, sortable=True),
    SearchableField("content", type=SearchFieldDataType.String),
    SearchField(
        "content_vector",
        type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
        searchable=True,
        vector_search_dimensions=1536,
        vector_search_profile_name="hnsw-cosine",
    ),
]
```

**Semantic configuration** also needed for re-ranking.

## Query Routing Architecture

Route queries by intent before hitting any search layer:

| Query type | Example | Route |
|------------|---------|-------|
| Numeric / aggregation | "average HbA1c last year?" | Supabase SQL on `patient_observations` |
| Temporal + structured | "medications I was on in 2024?" | Supabase SQL on `patient_medications` |
| Narrative / semantic | "what did my cardiologist say?" | Azure AI Search hybrid |
| Mixed | "was kidney function normal after antibiotics?" | Both, merge context |

**Do not send numeric aggregation queries to Azure AI Search** — it does not aggregate. These must go to Supabase.

## Query Rewriting via Claude

For complex clinical queries, a lightweight pre-retrieval step via Claude:

1. Analyze intent (aggregation vs. narrative vs. mixed)
2. Identify target document family (`structured_lab`, `imaging_narrative`, etc.)
3. Resolve temporal references ("last year" → `2025-01-01` to `2025-12-31`)
4. Expand clinical abbreviations: `HbA1c` → `hemoglobina glicada`, `PA` → `pressão arterial`
5. Build structured filter expression for Azure AI Search

```python
# Example rewritten query result
{
    "route": "hybrid_search",
    "search_text": "hemoglobina glicada hemoglobin a1c",
    "filter": "document_family eq 'structured_lab' and collection_date ge 2025-01-01",
    "top_k": 5,
}
```

## Context Assembly (What to Inject into Claude)

Replace 500-char raw text truncations with structured entity extraction:

**Priority order for each retrieved document:**
1. `structured_data.findings[]` — for labs: name, value, unit, flag, reference range
2. `structured_data.summary` — available for all document families
3. `structured_data.entities_for_memory` — pre-extracted key entities
4. `raw_clinical_text[:500]` — only as fallback when structured data absent

**Context block per document (target <300 tokens):**
```
[Lab Report — 2024-08-15]
- HbA1c: 7.8% (ref: <5.7%) — HIGH
- Fasting glucose: 142 mg/dL (ref: 70-99) — HIGH
- Creatinine: 0.9 mg/dL — normal
Summary: Suboptimal glycemic control. Recommend endocrinology follow-up.
```

## Negation Handling

**"No fever" ≠ "fever"** is unsolvable at the retrieval layer — BM25 and vector similarity both retrieve documents mentioning the term regardless of negation context.

**Correct mitigation:** System prompt instruction to Claude:
```
When a finding is prefixed with negation terms (no, ausência de, sem, nega, descarta),
treat it as the ABSENCE of that finding, not its presence.
```

Do not attempt negation-aware retrieval — the cost/complexity is not justified at this scale.

## Evaluation Without Labeled Data

1. **Synthetic query hit-rate testing** — generate known queries from existing documents (e.g., "what was my HbA1c on [date]?" when that value exists in the index), measure retrieval recall
2. **Claude-as-judge faithfulness scoring** — for a sample of retrieved context + Claude answer pairs, prompt Claude to rate whether the answer is grounded in the provided context
3. **Schema conformance** — structured query results must conform to Pydantic models; non-conforming = retrieval failure

## Implementation Sequence

1. Rebuild Azure AI Search index with vector + metadata fields
2. Add embedding call on upload (generate `content_vector` from structured context block)
3. Replace `retriever.py` BM25 query with hybrid `VectorizedQuery` + `search_text`
4. Add query intent classifier + rewriter in chat pipeline
5. Replace raw-text context assembly with structured entity context blocks
6. Add numeric/aggregation route to Supabase SQL
7. Wire semantic re-ranking (Standard tier only — verify current tier first)

## Key Risks

- **Azure AI Search tier** — verify current tier supports vector fields (Basic tier does not); upgrade to Standard if needed
- **Embedding cost** — generating embeddings on every upload adds latency and API cost; batch during off-peak or use Azure's built-in vectorization if available
- **Index migration** — existing indexed documents have no `content_vector`; must re-index all after rebuild
- **Backfill** — re-indexing existing documents with structured context blocks requires re-reading from Supabase, not re-running the full pipeline
