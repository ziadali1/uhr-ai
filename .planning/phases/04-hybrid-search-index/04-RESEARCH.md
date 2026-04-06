# Phase 4: Hybrid Search Index — Research

**Researched:** 2026-04-06
**Domain:** Azure AI Search vector fields, Azure OpenAI embeddings, hybrid RRF search
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- D-01: Do NOT embed `anonymized_text`. Embed a lightweight structured context block from `structured_result` fields.
- D-02: Context block assembly order: summary → entities_for_memory → lab findings (name/value/unit/flag) → imaging impression/findings → diagnoses/symptoms/allergies/medications.
- D-03: If `structured_result` is null or missing all fields → fall back to first 1000 chars of `anonymized_text`.
- D-04: Block format: compact plain text, fields separated by newlines, no JSON. Max ~500 tokens → truncate at ~2000 chars. No headers needed.
- D-05: This is Phase 4's pragmatic approximation; Phase 5 builds the canonical assembler.
- D-06: Azure OpenAI embeddings only. No second provider.
- D-07: Model: `text-embedding-3-small` (1536-dim output).
- D-08: Deployment name from env var `AZURE_OPENAI_EMBEDDING_DEPLOYMENT`. Endpoint/key reuse `AZURE_OPENAI_BASE_URL` / `AZURE_OPENAI_API_KEY`.
- D-09: Phase includes provisioning the Azure embedding deployment if not already available.
- D-10: Embedding generation is a network call — wrap in try/except. Failure logs and skips (soft-fail). Does not block upload.
- D-11: One vector per document. Same index cardinality as current system.
- D-12: No passage-level chunking in Phase 4.
- D-13: Each index document corresponds to one uploaded document (one `doc_id`).
- D-14: Drop + recreate the index. Delete existing index, define new schema, re-index all documents.
- D-15: Brief search downtime during migration is acceptable (single-user personal system).
- D-16: Re-index script: iterate all documents with non-null `anonymized_text` (or `structured_result`), assemble context block, generate embedding, upload to new index. Must be idempotent (safe to re-run).
- D-17: Documents with `document_family = 'unknown'` and null `structured_result` → use anonymized_text fallback.
- D-18: New fields: `content_vector` (1536-dim float32, HNSW cosine), `document_family` (filterable string), `collection_date` (filterable ISO date string), `document_subtype` (filterable string, optional). Plus semantic configuration named `uhr-semantic` pointing at `content` as primary content field.
- D-19: Existing fields `content`, `source_name`, `entities` remain unchanged.
- D-20: Replace current search with: `VectorizedQuery(vector=query_embedding, k_nearest_neighbors=50, fields="content_vector")` + `search_text=query` + `query_type="semantic"` + RRF fusion.
- D-21: Top-k remains 3 by default.
- D-22: Retriever generates its own embedding for the query text before the hybrid search call.
- D-23: Mock mode must continue working. In mock mode: skip embedding generation, use existing `_mock_search`.
- D-24: `USE_MOCK_AZURE` guard in `search.py` covers this — extend to the new embeddings service.

### Claude's Discretion
- Internal function signatures for `generate_embedding()` and `assemble_context_block()`
- Whether `embeddings.py` and context block assembler are in `services/azure/` or `services/rag/`
- Exact env var names for Azure embedding endpoint/key (follow existing conventions)
- Error logging format for embedding failures
- Whether re-index script is a standalone CLI script or a `/admin/reindex` endpoint

### Deferred Ideas (OUT OF SCOPE)
- Passage-level chunking (post-Phase 4)
- Canonical structured context block assembler (Phase 5, RETRIEVE-05)
- Query intent routing (Phase 5, RETRIEVE-04)
- Re-ranking with cross-encoder (future)
- Multi-vector per document (future)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| RETRIEVE-01 | Azure AI Search index includes vector fields (1536-dim, HNSW), filterable metadata (`document_family`, `collection_date`, `document_subtype`), and semantic configuration | SDK classes for SearchField, VectorSearch, HnswAlgorithmConfiguration, SemanticConfiguration verified in §Standard Stack and §Code Examples |
| RETRIEVE-02 | System generates embeddings from structured context blocks (not raw text) on each document upload | `generate_embedding()` pattern + `assemble_context_block()` pattern documented; integration point in `upload.py` confirmed |
| RETRIEVE-03 | Chat retrieval uses hybrid search (vector + keyword + RRF) instead of BM25-only | VectorizedQuery + search_text + query_type="semantic" syntax confirmed; retriever update path documented |
</phase_requirements>

---

## Summary

Phase 4 upgrades the Azure AI Search index from keyword-only (BM25) to hybrid search: vector similarity via HNSW + BM25 keyword + RRF fusion with semantic reranking. The current codebase already has `azure-search-documents==11.6.0b4` installed, which fully supports vector fields — no SDK upgrade is required. The existing Azure OpenAI integration (`llm.py`) uses `openai.OpenAI(base_url=..., api_key=...)` with `AZURE_OPENAI_BASE_URL` and `AZURE_OPENAI_API_KEY` env vars; the embeddings service will reuse this same client pattern with one additional env var for the embedding deployment name.

The `StructuredResult` model stores subtype data in `structured_data: dict[str, Any]` (not a typed Pydantic union discriminator). Context block assembly must dispatch on `document_family` string and reconstruct the appropriate subtype model (e.g., `StructuredLab(**structured_result.structured_data)`) before accessing typed fields. The re-index script queries Supabase for all documents, assembles context blocks, generates embeddings, and uploads to the new index in batches of up to 1000 documents per Azure AI Search API call.

Azure AI Search Basic tier **does support vector search** (confirmed by official docs, March 2026). The max dimensions per vector field is 4096 on all tiers. The vector quota is 5 GB per partition for new Basic services created after April 3, 2024. No tier upgrade is required unless the existing service predates July 2023 (where quota is only 0.5 GB). Tier verification is still a required plan step to document the actual service tier and creation date.

**Primary recommendation:** Implement in the order: schema → embeddings.py → indexer update → retriever update → re-index script. Each step is independently testable and the mock guard ensures no regression in local development.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| azure-search-documents | 11.6.0b4 (installed) | Azure AI Search SDK — index management, upload, hybrid query | Already installed; supports vector fields, VectorizedQuery, SemanticConfiguration |
| openai | >=1.0.0 (installed) | Azure OpenAI client — embeddings API | Already used in `llm.py` with existing env vars |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| azure.core.credentials | (part of azure-core, already installed) | AzureKeyCredential for SearchIndexClient | Index schema management (create/delete) |
| supabase | 2.4.6 (installed) | Re-index script: query all documents from Supabase | Re-index script only |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| openai.OpenAI(base_url=...) | openai.AzureOpenAI(azure_endpoint=..., api_version=...) | Both work; project already uses OpenAI client with base_url pattern in llm.py — consistency wins |
| drop+recreate index | index migration in-place | Drop+recreate is simpler and correct since single-user system allows brief downtime (D-14) |

**Installation:** No new packages required. All dependencies are already in `requirements.txt`.

**Version verification:** `azure-search-documents==11.6.0b4` — released May 2024. Stable `11.6.0` released October 2025. The installed beta has full vector search support; the main difference is the stable release has fewer rough edges. For this project the installed version is sufficient.

---

## Architecture Patterns

### Recommended Project Structure
```
backend/
├── services/
│   ├── azure/
│   │   ├── search.py          # MODIFIED: IndexedDocument + index_document() + search()
│   │   └── embeddings.py      # NEW: generate_embedding(text) -> list[float] | None
│   └── rag/
│       ├── context_block.py   # NEW: assemble_context_block(sr, anon_text) -> str
│       ├── indexer.py         # MODIFIED: calls assemble_context_block + generate_embedding
│       └── retriever.py       # MODIFIED: embed query + hybrid search
├── scripts/
│   ├── setup_azure_search.py  # MODIFIED: new schema (drop+recreate)
│   └── reindex_documents.py   # NEW: re-index script
└── tests/
    └── rag/                   # NEW test directory
        ├── test_context_block.py
        └── test_embeddings.py
```

### Pattern 1: Index Schema Definition (vector + metadata + semantic)
**What:** Define `SearchIndex` with HNSW vector field, filterable metadata fields, and semantic configuration.
**When to use:** In `setup_azure_search.py` and the re-index script's drop+recreate step.
**Example:**
```python
# Source: https://learn.microsoft.com/en-us/azure/search/search-get-started-vector
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex, SearchField, SearchFieldDataType,
    SimpleField, SearchableField,
    VectorSearch, HnswAlgorithmConfiguration, VectorSearchProfile,
    SemanticConfiguration, SemanticSearch, SemanticPrioritizedFields, SemanticField,
)
from azure.core.credentials import AzureKeyCredential

fields = [
    SimpleField(name="id", type=SearchFieldDataType.String, key=True),
    SimpleField(name="user_id", type=SearchFieldDataType.String, filterable=True),
    SearchableField(name="content", type=SearchFieldDataType.String),
    SearchableField(name="entities", type=SearchFieldDataType.String),
    SimpleField(name="source_name", type=SearchFieldDataType.String, retrievable=True),
    # New Phase 4 fields:
    SearchField(
        name="content_vector",
        type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
        searchable=True,
        vector_search_dimensions=1536,
        vector_search_profile_name="uhr-hnsw-profile",
    ),
    SimpleField(name="document_family", type=SearchFieldDataType.String, filterable=True),
    SimpleField(name="collection_date", type=SearchFieldDataType.String, filterable=True),
    SimpleField(name="document_subtype", type=SearchFieldDataType.String, filterable=True),
]

vector_search = VectorSearch(
    algorithms=[HnswAlgorithmConfiguration(name="uhr-hnsw-config")],
    profiles=[VectorSearchProfile(
        name="uhr-hnsw-profile",
        algorithm_configuration_name="uhr-hnsw-config",
    )],
)

semantic_config = SemanticConfiguration(
    name="uhr-semantic",
    prioritized_fields=SemanticPrioritizedFields(
        content_fields=[SemanticField(field_name="content")],
    ),
)

index = SearchIndex(
    name=index_name,
    fields=fields,
    vector_search=vector_search,
    semantic_search=SemanticSearch(configurations=[semantic_config]),
)
client.create_or_update_index(index)
```

### Pattern 2: VectorizedQuery Hybrid Search
**What:** Combine VectorizedQuery with search_text for hybrid RRF + semantic reranking.
**When to use:** In updated `retriever.py` `search()` call.
**Example:**
```python
# Source: https://learn.microsoft.com/en-us/azure/search/search-get-started-vector
from azure.search.documents.models import VectorizedQuery

vector_query = VectorizedQuery(
    vector=query_embedding,         # list[float], 1536 dims
    k_nearest_neighbors=50,
    fields="content_vector",
)

results = client.search(
    search_text=query,
    vector_queries=[vector_query],
    filter=f"user_id eq '{user_id}'",
    query_type="semantic",
    semantic_configuration_name="uhr-semantic",
    select=["id", "content", "source_name"],
    top=top_k,
)
```

### Pattern 3: Azure OpenAI Embedding Generation
**What:** Call `text-embedding-3-small` via existing OpenAI client pattern.
**When to use:** In `embeddings.py` `generate_embedding()`, and in `retriever.py` to embed the query.
**Example:**
```python
# Source: https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/embeddings
import os
from openai import OpenAI

def _get_embedding_client() -> OpenAI:
    return OpenAI(
        base_url=os.environ["AZURE_OPENAI_BASE_URL"],
        api_key=os.environ["AZURE_OPENAI_API_KEY"],
    )

def generate_embedding(text: str) -> list[float] | None:
    if _use_mock():
        return None
    deployment = os.environ["AZURE_OPENAI_EMBEDDING_DEPLOYMENT"]
    try:
        client = _get_embedding_client()
        response = client.embeddings.create(input=text, model=deployment)
        return response.data[0].embedding  # list[float], 1536 dims
    except Exception as e:
        logger.error("embedding generation failed: %s", e)
        return None
```

### Pattern 4: Context Block Assembly (dispatch on document_family)
**What:** `StructuredResult.structured_data` is `dict[str, Any]`. Reconstruct the subtype model using the `document_family` discriminator.
**When to use:** In `context_block.py` `assemble_context_block()`.
**Example:**
```python
from models.document import (
    StructuredResult, StructuredLab, ImagingReport,
    ClinicalNote, MedicationDocument,
)

def assemble_context_block(sr: StructuredResult | None, anonymized_text: str) -> str:
    if sr is None:
        return anonymized_text[:1000]

    parts: list[str] = []
    data = sr.structured_data  # dict[str, Any]
    family = sr.document_family

    # Always include top-level fields
    if sr.entities_for_memory:
        parts.extend(sr.entities_for_memory)

    try:
        if family == "structured_lab":
            lab = StructuredLab(**data)
            if lab.summary:
                parts.append(lab.summary)
            if lab.entities_for_memory:
                parts.extend(lab.entities_for_memory)
            for f in lab.findings:
                flag = f" [{f.flag}]" if f.flag else ""
                unit = f" {f.unit}" if f.unit else ""
                parts.append(f"{f.name}: {f.value}{unit}{flag}")

        elif family == "imaging_narrative":
            img = ImagingReport(**data)
            if img.summary:
                parts.append(img.summary)
            if img.entities_for_memory:
                parts.extend(img.entities_for_memory)
            if img.impression:
                parts.append(img.impression)
            if img.findings:
                parts.append(img.findings)

        elif family == "clinical_narrative":
            note = ClinicalNote(**data)
            if note.summary:
                parts.append(note.summary)
            if note.entities_for_memory:
                parts.extend(note.entities_for_memory)
            parts.extend(note.diagnoses)
            parts.extend(note.symptoms)
            parts.extend(note.allergies)
            parts.extend(note.medications)

        elif family == "medication_document":
            med = MedicationDocument(**data)
            if med.summary:
                parts.append(med.summary)
            if med.entities_for_memory:
                parts.extend(med.entities_for_memory)
            for entry in med.medications:
                parts.append(entry.name + (f" {entry.dose}" if entry.dose else ""))

    except Exception:
        pass  # partial data is fine; fall through

    block = "\n".join(p for p in parts if p)
    if not block.strip():
        return anonymized_text[:1000]

    return block[:2000]  # ~500 token ceiling
```

### Pattern 5: Drop and Recreate Index
**What:** Delete the existing index if it exists, then create the new schema.
**When to use:** In `setup_azure_search.py` (rewritten) and re-index script.
**Example:**
```python
from azure.search.documents.indexes import SearchIndexClient
from azure.core.credentials import AzureKeyCredential

index_client = SearchIndexClient(endpoint, AzureKeyCredential(key))

# Drop existing
try:
    index_client.delete_index(index_name)
    print(f"Dropped existing index '{index_name}'")
except Exception:
    pass  # didn't exist; fine

# Recreate
index_client.create_or_update_index(index)
print(f"Created new index '{index_name}'")
```

### Pattern 6: Bulk Upload with Batching
**What:** `upload_documents()` accepts up to 1000 documents per batch. For re-index: batch in groups of 100 to stay well under the 16 MB payload limit.
**When to use:** In `reindex_documents.py` re-index script.
**Example:**
```python
from azure.search.documents import SearchClient

def _batch_upload(client: SearchClient, docs: list[dict], batch_size: int = 100) -> int:
    """Returns count of successfully uploaded documents."""
    uploaded = 0
    for i in range(0, len(docs), batch_size):
        batch = docs[i:i + batch_size]
        try:
            results = client.upload_documents(documents=batch)
            uploaded += sum(1 for r in results if r.succeeded)
        except Exception as e:
            logger.error("batch upload failed (offset=%d): %s", i, e)
    return uploaded
```

### Anti-Patterns to Avoid
- **algorithmConfigurationName (camelCase):** The Python SDK uses `algorithm_configuration_name` (snake_case) in `VectorSearchProfile`. Using camelCase silently fails with a 400 error from the REST API.
- **Omitting vector_search_profile_name on SearchField:** The vector field must reference a profile name that matches one defined in `VectorSearch.profiles`. Mismatched names cause index creation to fail.
- **Passing vector=None to upload_documents:** If `generate_embedding()` returns None, omit `content_vector` from the document dict entirely (or set to an empty list). Including a None value causes a serialization error. Omitting it is safe — the document indexes for BM25 only.
- **Using AzureOpenAI client instead of OpenAI:** The existing project uses `openai.OpenAI(base_url=..., api_key=...)` (not `openai.AzureOpenAI`). Do not introduce a second client pattern.
- **Re-indexing inside the upload request handler:** Embedding generation can take 200–500ms. The re-index script should run offline, not inside a live request.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| RRF score fusion | Custom merging of BM25 and vector result lists | `VectorizedQuery` + `search_text` together — Azure AI Search does RRF automatically | Rank fusion has subtle ordering edge cases; Azure's built-in implementation is proven |
| Retry logic for embeddings | Custom sleep/retry loop | OpenAI Python SDK retries automatically (2 retries with exponential backoff for 429/500/connection errors) | The openai library already handles the common retry cases |
| Batch size calculation for upload_documents | Custom byte estimator | Use a fixed batch_size=100; Azure enforces max 1000 docs per call and 16 MB payload | 100 docs of clinical text is well under the 16 MB limit; no dynamic sizing needed |
| Semantic configuration evaluation | Custom reranking logic | `query_type="semantic"` + `semantic_configuration_name` — Azure handles L2 semantic reranking | Cross-encoder reranking is expensive and complex; Azure's semantic ranker is built-in |

**Key insight:** Azure AI Search's hybrid search (BM25 + HNSW + RRF + semantic reranking) is a four-stage pipeline. Each stage is handled internally by the service — the SDK call only needs to specify which stages to activate via `vector_queries`, `search_text`, `query_type`, and `semantic_configuration_name`.

---

## Common Pitfalls

### Pitfall 1: VectorSearchProfile Name Mismatch
**What goes wrong:** `SearchField.vector_search_profile_name` references a profile name that doesn't match any entry in `VectorSearch.profiles`. The index creation call returns a 400 error with a message about an unknown profile.
**Why it happens:** The name strings must match exactly (case-sensitive). Easy to introduce a typo when using different string literals in the field definition vs. the profile list.
**How to avoid:** Define the profile name as a module-level constant and reference it in both places.
**Warning signs:** `azure.core.exceptions.HttpResponseError: (InvalidRequestBody)` during `create_or_update_index()`.

### Pitfall 2: Including null/None in content_vector Field
**What goes wrong:** Including `"content_vector": None` in an upload_documents payload causes a serialization error. The field type is `Collection(Edm.Single)` — it accepts a list or must be omitted.
**Why it happens:** Python dataclasses and dicts pass through None values. A soft-fail `generate_embedding()` returns None; if the caller blindly includes it in the document dict, the upload fails.
**How to avoid:** In `index_document()`, conditionally add `content_vector` to the dict only when the value is a non-empty list.
**Warning signs:** `azure.core.exceptions.HttpResponseError: (InvalidRequestBody) Content field has an invalid value`.

### Pitfall 3: StructuredResult.structured_data is a Raw Dict
**What goes wrong:** `StructuredResult.structured_data` is typed as `dict[str, Any]` — it is NOT a Pydantic model. Accessing `.findings` directly on it raises `AttributeError`. This is by design (JSONB storage), but easy to miss.
**Why it happens:** The model uses a raw dict for JSONB flexibility. The subtype models (`StructuredLab`, `ImagingReport`, etc.) must be reconstructed via `StructuredLab(**structured_data)`.
**How to avoid:** Always dispatch on `document_family` first, then construct the typed subtype model before accessing typed fields. Wrap in try/except for robustness against partial/corrupted data.
**Warning signs:** `AttributeError: 'dict' object has no attribute 'findings'` in `assemble_context_block()`.

### Pitfall 4: Semantic Ranker Requires search_text
**What goes wrong:** `query_type="semantic"` with `search_text=None` or `search_text=""` falls back to pure vector search without semantic reranking. The semantic ranker requires a non-empty keyword query to operate.
**Why it happens:** Semantic ranking is a post-retrieval step applied to the combined BM25 + vector candidate set. If there is no text query, there is no BM25 candidate set to rerank.
**How to avoid:** Always pass both `search_text=query` and `vector_queries=[...]` in hybrid mode. Never pass an empty string for `search_text`.
**Warning signs:** Results are returned but `@search.reranker_score` is absent or 0 in the response.

### Pitfall 5: Azure OpenAI Embedding Deployment vs. Chat Deployment
**What goes wrong:** Using the chat deployment name (`gpt-4o-mini`) for the embeddings call. Azure OpenAI requires separate deployments for chat vs. embedding models.
**Why it happens:** The existing `AZURE_OPENAI_CHAT_DEPLOYMENT` env var is for `gpt-4o-mini`. Reusing it for embeddings results in a 404 (deployment not found for that model type).
**How to avoid:** Add `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` env var (D-08). Verify the deployment exists in Azure Portal before running.
**Warning signs:** `openai.NotFoundError: The deployment 'gpt-4o-mini' was not found for model 'text-embedding-3-small'`.

### Pitfall 6: Basic Tier Vector Quota on Old Services
**What goes wrong:** If the Azure AI Search service was created before July 1, 2023, the vector quota is only 0.5 GB per partition. Re-indexing all documents with 1536-dim float32 vectors could exhaust this quota.
**Why it happens:** Azure increased vector quotas significantly in April–May 2024 for new and upgraded services.
**How to avoid:** Verify service creation date in Azure Portal. For new services (post-April 2024), 5 GB quota is ample for a single-user record system. If the service is old and quota is limited, upgrade the service (Azure supports Basic → Standard in-place for existing services).
**Warning signs:** `azure.core.exceptions.HttpResponseError` with message about vector quota exceeded during re-index.

---

## Code Examples

### Full schema creation (verified pattern)
```python
# Source: https://learn.microsoft.com/en-us/azure/search/search-get-started-vector
# SemanticField constructor uses field_name= (not name=) in current SDK
semantic_config = SemanticConfiguration(
    name="uhr-semantic",
    prioritized_fields=SemanticPrioritizedFields(
        content_fields=[SemanticField(field_name="content")],
    ),
)
```

### Hybrid search call (verified pattern)
```python
# Source: https://learn.microsoft.com/en-us/python/api/azure-search-documents/azure.search.documents.models.vectorizedquery
vector_query = VectorizedQuery(
    vector=query_embedding,     # Required: list[float]
    k_nearest_neighbors=50,     # Candidate pool before reranking
    fields="content_vector",    # Must match the field name in the index
)
results = client.search(
    search_text=query,
    vector_queries=[vector_query],
    filter=f"user_id eq '{user_id}'",
    query_type="semantic",
    semantic_configuration_name="uhr-semantic",
    select=["id", "content", "source_name"],
    top=3,
)
```

### Embedding call (verified pattern)
```python
# Source: https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/embeddings
# Uses openai.OpenAI with base_url (project's existing pattern from llm.py)
from openai import OpenAI
client = OpenAI(
    base_url=os.environ["AZURE_OPENAI_BASE_URL"],
    api_key=os.environ["AZURE_OPENAI_API_KEY"],
)
response = client.embeddings.create(
    input=text,
    model=os.environ["AZURE_OPENAI_EMBEDDING_DEPLOYMENT"],
)
embedding: list[float] = response.data[0].embedding  # length 1536
```

### Document upload with conditional vector field
```python
# Do NOT include content_vector if vector is None
doc = {
    "id": doc_id,
    "user_id": user_id,
    "content": text,
    "source_name": source_name,
    "entities": ", ".join(entities),
    "document_family": document_family or "unknown",
    "collection_date": collection_date,
    "document_subtype": document_subtype,
}
if vector:  # only add if non-None and non-empty
    doc["content_vector"] = vector
client.upload_documents(documents=[doc])
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| BM25 keyword-only search | Hybrid: BM25 + HNSW vector + RRF + semantic reranking | SDK support since azure-search-documents 11.4 (2023) | Substantially better recall on semantic queries ("what did my cardiologist say about my heart?") |
| `algorithmConfigurationName` (REST camelCase) | `algorithm_configuration_name` (Python snake_case) | SDK 11.4+ | Python SDK parameter must use snake_case |
| Separate `VectorSearch` and `SemanticConfiguration` configs | Same — still separate configs, but both attach to `SearchIndex` | Stable since 11.6.0 | No change, just confirm correct attachment points |

**Deprecated/outdated:**
- `ExhaustiveKnnAlgorithmConfiguration`: exists as an alternative to HNSW for exact search; not recommended for production use (much slower at scale). Use `HnswAlgorithmConfiguration`.
- `VectorizableTextQuery`: a newer pattern that delegates embedding generation to Azure. Do NOT use — this project generates embeddings server-side (D-06/D-22).

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| azure-search-documents | Index schema + hybrid search | Yes (in requirements.txt) | 11.6.0b4 | — |
| openai | Embedding generation | Yes (in requirements.txt) | >=1.0.0 | — |
| Azure AI Search service | Re-index + search | Must verify in Azure Portal | Unknown | Mock mode for local dev |
| Azure OpenAI embedding deployment | generate_embedding() | Must provision if not exists | Unknown | Mock mode for local dev |
| Python 3.x + pip | Run scripts | Yes (project runs) | Unknown | — |
| Supabase (live DB) | Re-index script: read all documents | Yes (used in Phase 3) | — | — |

**Missing dependencies with no fallback:**
- Azure AI Search service tier/creation date: must verify in Azure Portal to confirm vector quota sufficiency before running re-index. If the service was created before July 2023, vector quota is only 0.5 GB — may need service upgrade.
- Azure OpenAI embedding deployment (`text-embedding-3-small`): must be provisioned in Azure Portal before running. Plan must include this as an explicit setup step (D-09).

**Missing dependencies with fallback:**
- All local development and unit testing works in mock mode (`USE_MOCK_AZURE=true`) with no Azure services required.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.2.0 (installed) |
| Config file | None detected — tests use `sys.path.insert` pattern |
| Quick run command | `cd backend && python -m pytest tests/rag/ -x -q` |
| Full suite command | `cd backend && python -m pytest tests/ -x -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| RETRIEVE-01 | Index schema includes vector field, filterable fields, semantic config | unit (schema construction) | `pytest tests/rag/test_search_schema.py -x` | No — Wave 0 |
| RETRIEVE-02 | `assemble_context_block()` produces correct output per document family | unit | `pytest tests/rag/test_context_block.py -x` | No — Wave 0 |
| RETRIEVE-02 | `generate_embedding()` returns list[float] on success, None on failure | unit | `pytest tests/rag/test_embeddings.py -x` | No — Wave 0 |
| RETRIEVE-02 | `index_after_upload()` calls embedding generation and passes vector | unit | `pytest tests/rag/test_indexer.py -x` | No — Wave 0 |
| RETRIEVE-03 | `build_context_prompt()` uses VectorizedQuery in real mode | unit (mock SearchClient) | `pytest tests/rag/test_retriever.py -x` | No — Wave 0 |
| RETRIEVE-03 | Hybrid query returns more relevant results than BM25 on 10 clinical queries | manual / smoke | N/A — human verification | N/A |
| All | Chat endpoint still works after retriever change | smoke | `pytest tests/ -x -q` (full suite) | Partially |

### Unit Test Pattern: `assemble_context_block()`
```python
# tests/rag/test_context_block.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from models.document import StructuredResult, StructuredLab, LabFinding, ImagingReport, ClinicalNote
from services.rag.context_block import assemble_context_block

def test_lab_block_contains_findings():
    sr = StructuredResult(
        document_family="structured_lab",
        structured_data=StructuredLab(
            summary="CBC normal",
            findings=[LabFinding(name="Hemoglobina", value="14.5", unit="g/dL", flag="normal")],
        ).model_dump(),
    )
    block = assemble_context_block(sr, "fallback text")
    assert "Hemoglobina" in block
    assert "14.5" in block
    assert "g/dL" in block
    assert "normal" in block

def test_imaging_block_contains_impression():
    sr = StructuredResult(
        document_family="imaging_narrative",
        structured_data=ImagingReport(impression="Pulmões sem alterações").model_dump(),
    )
    block = assemble_context_block(sr, "fallback text")
    assert "Pulmões sem alterações" in block

def test_null_sr_falls_back_to_anonymized():
    block = assemble_context_block(None, "fallback text 12345")
    assert "fallback text 12345" in block

def test_block_truncated_at_2000_chars():
    sr = StructuredResult(
        document_family="clinical_narrative",
        structured_data=ClinicalNote(diagnoses=["D" * 3000]).model_dump(),
    )
    block = assemble_context_block(sr, "fallback")
    assert len(block) <= 2000
```

### Unit Test Pattern: `generate_embedding()`
```python
# tests/rag/test_embeddings.py
from unittest.mock import patch, MagicMock
import os
os.environ["USE_MOCK_AZURE"] = "false"  # force real path for test

from services.azure.embeddings import generate_embedding

def test_generate_embedding_returns_list_of_floats(monkeypatch):
    mock_response = MagicMock()
    mock_response.data = [MagicMock(embedding=[0.1] * 1536)]
    with patch("services.azure.embeddings._get_embedding_client") as mock_client_fn:
        mock_client = MagicMock()
        mock_client.embeddings.create.return_value = mock_response
        mock_client_fn.return_value = mock_client
        result = generate_embedding("blood test hemoglobin 14.5")
    assert isinstance(result, list)
    assert len(result) == 1536

def test_generate_embedding_returns_none_on_failure(monkeypatch):
    with patch("services.azure.embeddings._get_embedding_client") as mock_client_fn:
        mock_client = MagicMock()
        mock_client.embeddings.create.side_effect = Exception("network error")
        mock_client_fn.return_value = mock_client
        result = generate_embedding("test text")
    assert result is None

def test_generate_embedding_mock_mode_returns_none():
    import os
    os.environ["USE_MOCK_AZURE"] = "true"
    import importlib, services.azure.embeddings as emb_mod
    importlib.reload(emb_mod)  # reset _use_mock_cache
    result = emb_mod.generate_embedding("test text")
    assert result is None
```

### Integration Test Pattern: VectorizedQuery is Sent (not BM25-only)
```python
# tests/rag/test_retriever.py
from unittest.mock import patch, MagicMock, call
import os
os.environ["USE_MOCK_AZURE"] = "false"

from services.rag.retriever import build_context_prompt

def test_hybrid_search_sends_vector_queries():
    """Verify retriever passes vector_queries= to SearchClient.search()."""
    mock_embedding = [0.0] * 1536
    with patch("services.rag.retriever.generate_embedding", return_value=mock_embedding), \
         patch("services.azure.search.SearchClient") as mock_sc_class:
        mock_sc = MagicMock()
        mock_sc.search.return_value = []
        mock_sc_class.return_value = mock_sc

        build_context_prompt("what is my hemoglobin?", "user-1")

        call_kwargs = mock_sc.search.call_args.kwargs
        assert "vector_queries" in call_kwargs
        assert len(call_kwargs["vector_queries"]) == 1
        assert call_kwargs["query_type"] == "semantic"
```

### Verification Approach: Re-index Completeness
After running the re-index script, verify all documents have non-null vectors using Azure AI Search's REST API or SDK:

```python
# scripts/verify_reindex.py — run after reindex_documents.py completes
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential

client = SearchClient(endpoint, index_name, AzureKeyCredential(key))

# Count documents with missing content_vector
results = client.search(
    search_text="*",
    filter="user_id eq 'dev-user-id'",
    select=["id", "content_vector"],
    top=1000,
)

missing_vector = [r["id"] for r in results if not r.get("content_vector")]
total = sum(1 for _ in client.search(search_text="*", select=["id"], top=1000))

print(f"Total documents: {total}")
print(f"Missing vectors: {len(missing_vector)}")
if missing_vector:
    print("IDs with missing vectors:", missing_vector[:10])
```

### Regression Check for Chat Functionality
The existing chat integration test suite covers `build_context_prompt()` and the full chat flow. After the retriever update:

1. Run full test suite: `cd backend && python -m pytest tests/ -x -q`
2. Verify mock mode still works end-to-end: `USE_MOCK_AZURE=true python -m pytest tests/ -q`
3. Manual smoke test: start the server in mock mode and ask 3 sample questions — verify responses are not empty and sources are cited.

The key regression risk is that the new hybrid `search()` call changes the `SearchResult` return format (adding `@search.reranker_score`). The existing `retriever.py` accesses `r["@search.score"]` — this must still be present in hybrid mode (RRF score). Verify the field name in the result dict after the switch.

### Sampling Rate
- **Per task commit:** `cd backend && python -m pytest tests/rag/ -x -q`
- **Per wave merge:** `cd backend && python -m pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/rag/__init__.py` — new test directory
- [ ] `backend/tests/rag/test_context_block.py` — covers RETRIEVE-02 (context block assembly)
- [ ] `backend/tests/rag/test_embeddings.py` — covers RETRIEVE-02 (embedding generation)
- [ ] `backend/tests/rag/test_indexer.py` — covers RETRIEVE-02 (indexer integration)
- [ ] `backend/tests/rag/test_retriever.py` — covers RETRIEVE-03 (hybrid search)

---

## Sources

### Primary (HIGH confidence)
- [VectorizedQuery class — azure.search.documents Python SDK](https://learn.microsoft.com/en-us/python/api/azure-search-documents/azure.search.documents.models.vectorizedquery?view=azure-python) — constructor signature, parameters
- [VectorSearchProfile class — azure.search.documents Python SDK](https://learn.microsoft.com/en-us/python/api/azure-search-documents/azure.search.documents.indexes.models.vectorsearchprofile?view=azure-python) — confirmed `algorithm_configuration_name` (snake_case)
- [Quickstart: Vector Search — Azure AI Search](https://learn.microsoft.com/en-us/azure/search/search-get-started-vector) — complete index schema + hybrid search code
- [How to generate embeddings — Azure OpenAI](https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/embeddings) — embeddings.create() Python pattern, env vars
- [Service Limits — Azure AI Search](https://learn.microsoft.com/en-us/azure/search/search-limits-quotas-capacity) — confirmed Basic tier supports vector (4096 max dims, 5 GB quota for new services)
- [Choose a Service Tier — Azure AI Search](https://learn.microsoft.com/en-us/azure/search/search-sku-tier) — tier feature matrix, upgrade path

### Secondary (MEDIUM confidence)
- [Create a Vector Query — Azure AI Search](https://learn.microsoft.com/en-us/azure/search/vector-search-how-to-query) — hybrid query parameters, semantic reranker behavior with empty search_text
- [azure-search-documents PyPI page](https://pypi.org/project/azure-search-documents/) — version history (11.6.0b4 released May 2024, stable 11.6.0 October 2025)

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages already installed; SDK APIs verified against official docs
- Architecture: HIGH — patterns derived from official Azure docs and current SDK signatures
- Pitfalls: HIGH — most confirmed by SDK documentation or direct code analysis of existing codebase
- Tier requirements: HIGH — confirmed directly from official service limits docs (March 2026)

**Research date:** 2026-04-06
**Valid until:** 2026-07-06 (stable SDK; Azure AI Search feature set is mature)
