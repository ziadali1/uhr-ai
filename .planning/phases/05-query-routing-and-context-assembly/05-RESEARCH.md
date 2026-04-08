# Phase 5: Query Routing and Context Assembly — Research

**Researched:** 2026-04-08
**Domain:** LLM-driven query routing, SQL-structured retrieval, clinical context assembly (Python/FastAPI/Supabase)
**Confidence:** HIGH — all findings verified directly from the codebase

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01:** Use the LLM as the primary query interpreter — one call that classifies intent (`sql_only` | `search_only` | `mixed`), extracts entities, resolves temporal references, decides tool usage, and emits a structured routing plan.
**D-02:** The interpreter produces a structured output (Pydantic model or JSON): intent type, extracted entities, time range if relevant, sub-questions if mixed intent.
**D-03:** No regex/keyword fallback for primary classification. The LLM interpreter IS the router.
**D-04:** On interpreter failure: fall back to `search_only` with the original query. Soft-fail always.
**D-05:** Portuguese abbreviation expansion before the interpreter call: HbA1c → "hemoglobina glicada", PA → "pressão arterial", FC → "frequência cardíaca", FR → "frequência respiratória", SpO2 → "saturação de oxigênio".
**D-06:** LLM-extracted parameters injected into safe query templates (hybrid: template safety + LLM flexibility). LLM never generates free-form SQL.
**D-07:** Lightweight validation before SQL execution: allowlist tables/fields, enforce `user_id` scope in code (not LLM), reject mutations.
**D-08:** SQL targets patient tables (`patient_observations`, `patient_conditions`, `patient_medications`, `patient_allergies`, `patient_imaging_findings`). Not the `documents` table.
**D-09:** SQL failures soft-fail: log error, fall back to `search_only` or partial hybrid context.
**D-10:** Chat context assembler is a new component, separate from `context_block.py` (Phase 4, do NOT modify).
**D-11:** Chat context block per document: `[Fonte: {source_name} | {document_family} | {collection_date}]` + Summary + Findings + Entities. Plain text, max ~300 tokens.
**D-12:** SQL results come first in context, labeled as ground truth structured data.
**D-13:** Retrieved documents follow as supporting context.
**D-14:** Total context budget: ~2000 tokens (SQL ~800 + search ~1200). Reduce top-k 3→2 if SQL block is large.
**D-15:** Mixed intent: interpreter decomposes into sub-steps, each executed independently, results merged.
**D-16:** Single Claude synthesis call over unified context. No second dedicated synthesis call in Phase 5.
**D-17:** Router is a tool-using clinical reasoning agent — prototype/research framing.
**D-18:** Update `SYSTEM_PROMPT` in `retriever.py` to instruct Claude to reason over structured data first.
**D-19:** Keep existing rules: cite sources, never invent, never diagnose, respond in Brazilian Portuguese.

### Claude's Discretion

- LLM model used for the query interpreter (follow existing patterns — Azure OpenAI via `generate_json()` in `llm.py`)
- Exact Pydantic schema for the router's structured output
- Whether the router and assembler are separate files or combined in `services/rag/router.py`
- Token counting approach (character approximation is fine)
- Exact SQL template set (infer from `patient_observations` schema + Phase 2 context)
- Whether abbreviation expansion is a dict lookup or a small pre-processing function

### Deferred Ideas (OUT OF SCOPE)

- Multi-turn context memory (session memory across turns)
- Full natural language to SQL via unconstrained LLM generation
- Semantic caching of router results
- Citation linking (document ID → specific page)
- Re-ranking SQL results by clinical relevance
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| RETRIEVE-04 | System classifies query intent and routes numeric/aggregation queries to Supabase SQL, narrative queries to Azure AI Search | `router.py` implementing `route_query()` with `generate_json()` LLM call; Supabase client pattern verified in `patient_store.py` |
| RETRIEVE-05 | Context injected into Claude uses structured entity blocks (lab values, flags, summaries) not 500-char raw text truncations | Chat assembler reading `StructuredResult.structured_data` fields; replaces the `r.excerpt` raw OCR pattern in `retriever.py` |
</phase_requirements>

---

## Summary

Phase 5 replaces the flat `build_context_prompt()` pipeline in `retriever.py` with an LLM-driven routing and context assembly layer. The current implementation (51 lines) does: embed query → `search()` → format raw `excerpt` strings. There is no intent classification, no SQL path, and no structured context — Claude receives raw OCR fragments.

The new layer adds `services/rag/router.py` which (1) expands Portuguese abbreviations, (2) calls `generate_json()` once with the query to get a `RoutingResult` Pydantic object, (3) dispatches to SQL template executors and/or `search()` based on intent, and (4) assembles structured clinical context blocks for both SQL and search results. The refactored `build_context_prompt()` calls `route_query()` internally — the `chat.py` signature is unchanged.

The LLM stack is Azure OpenAI via the `openai` Python SDK. `generate_json()` in `llm.py` is the correct function for the router's interpreter call — it uses `response_format={"type": "json_object"}`, temperature=0, and max_tokens=4096. The `anthropic` SDK is installed (`anthropic==0.28.0`) but is NOT used by any existing service — all LLM calls go through Azure OpenAI. The planner should follow the Azure OpenAI path.

**Primary recommendation:** Build `router.py` with three sections: (1) abbreviation expander, (2) `route_query()` using `generate_json()` with a tight system prompt and Pydantic JSON parsing, (3) SQL executor functions using `_get_client()` from `supabase_store.py`. Refactor `retriever.py` to call `route_query()` and use the new chat context assembler instead of `r.excerpt`.

---

## Standard Stack

### Core (verified from requirements.txt and codebase)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `openai` | `>=1.0.0` | Azure OpenAI LLM calls (router interpreter) | Already used in `llm.py` and `embeddings.py`; all LLM calls go here |
| `supabase` | `2.4.6` | Patient table SQL queries | Already used in `patient_store.py` and `supabase_store.py` |
| `pydantic` | `2.7.1` | `RoutingResult` schema + all structured outputs | Already used project-wide; Pydantic 2.x, not v1 |
| `fastapi` | `0.111.0` | Web framework (no changes to router layer itself) | Existing framework |

### No New Dependencies Required

All libraries needed for Phase 5 are already installed. No `pip install` steps needed.

**Key confirmation:** The `instructor` library is NOT installed. The project uses `generate_json()` with `response_format={"type": "json_object"}` and manual `json.loads()` + Pydantic model construction. Phase 5 must follow the same pattern — no `instructor`.

---

## Architecture Patterns

### Existing File Structure (do not create new directories)

```
backend/
├── services/
│   ├── rag/
│   │   ├── context_block.py      # Phase 4 embedding assembler — READ ONLY
│   │   ├── retriever.py          # REFACTOR: build_context_prompt() internals
│   │   ├── indexer.py            # Unchanged
│   │   └── router.py             # NEW: route_query(), SQL executors, chat assembler
│   ├── azure/
│   │   ├── llm.py                # generate_json() — LLM pattern to follow
│   │   ├── embeddings.py         # _use_mock() pattern reference
│   │   └── search.py             # search() — called by router for search paths
│   ├── patient_store.py          # _get_client() reuse for SQL queries
│   └── supabase_store.py         # _get_client() original definition
├── models/
│   └── document.py               # StructuredLab, LabFinding, ImagingReport, etc.
└── tests/
    └── rag/
        ├── test_retriever.py     # Existing tests — must remain green
        └── test_router.py        # NEW: Wave 0 stubs for router
```

### Pattern 1: Mock Guard (replicate from `search.py` and `llm.py`)

```python
# Source: backend/services/azure/search.py lines 13-20
_use_mock_cache: bool | None = None

def _use_mock() -> bool:
    global _use_mock_cache
    if _use_mock_cache is None:
        _use_mock_cache = os.getenv("USE_MOCK_AZURE", "true").lower() == "true"
    return _use_mock_cache
```

In `router.py`: if `_use_mock()`, `route_query()` returns `RoutingResult(intent="search_only", ...)` immediately — no LLM call, no SQL calls.

### Pattern 2: LLM JSON Call (replicate from `llm.py`)

```python
# Source: backend/services/azure/llm.py lines 79-110
def generate_json(system: str, user: str) -> str:
    """Single-turn call for structured JSON extraction. Returns raw response string."""
    if _use_mock():
        return "{}"
    if len(user) > 12000:
        user = user[:12000] + "\n\n[texto truncado]"
    client = _get_client()
    response = client.chat.completions.create(
        model=deployment,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        max_tokens=4096,
        temperature=0,
        response_format={"type": "json_object"},
    )
    content = response.choices[0].message.content
    return content if content else "{}"
```

The router interpreter call uses `generate_json()` imported from `services.azure.llm`. Parse the returned string with `json.loads()` then construct `RoutingResult(**data)` in a try/except — failure falls back to `search_only`.

### Pattern 3: Supabase Client for SQL Queries

```python
# Source: backend/services/supabase_store.py lines 16-23
# and backend/services/patient_store.py line 49
from services.supabase_store import _get_client

# In router.py SQL executors — reuse exactly this singleton
client = _get_client()
results = (
    client.table("patient_observations")
    .select("normalized_analyte,value_str,unit,flag,observed_date")
    .eq("user_id", user_id)       # ALWAYS injected by code — never by LLM
    .eq("normalized_analyte", analyte_name)
    .order("observed_date", desc=True)
    .limit(10)
    .execute()
)
```

**Critical:** `user_id` scope is always appended by Python code. The LLM only extracts the parameter values (analyte name, date range, etc.).

### Pattern 4: Soft-Fail Exception Handling

```python
# Source: backend/services/patient_store.py lines 63-64
# Pattern: try/except Exception as e: logger.warning(...)
try:
    routing_result = _call_interpreter(expanded_query, user_id)
except Exception as e:
    logger.warning("route_query interpreter failed, falling back to search_only: %s", e)
    routing_result = RoutingResult(intent="search_only", search_queries=[question])
```

### Pattern 5: Pydantic 2.x Structured Output

```python
# Source: backend/models/document.py (entire file) — Pydantic 2.x BaseModel
from pydantic import BaseModel
from typing import Literal
from datetime import date

class RoutingResult(BaseModel):
    intent: Literal["sql_only", "search_only", "mixed"]
    entities: list[str] = []
    time_range: tuple[date, date] | None = None
    sql_steps: list[str] = []       # e.g. ["observations:HbA1c", "medications:active"]
    search_queries: list[str] = []  # expanded query strings for search()
```

### Pattern 6: Family Dispatch (replicate from `context_block.py`)

```python
# Source: backend/services/rag/context_block.py lines 40-102
if sr.document_family == "structured_lab":
    lab = StructuredLab(**sr.structured_data)
    # ... extract fields
elif sr.document_family == "imaging_narrative":
    report = ImagingReport(**sr.structured_data)
    # ... extract fields
elif sr.document_family == "clinical_narrative":
    note = ClinicalNote(**sr.structured_data)
    # ... extract fields
elif sr.document_family == "medication_document":
    med_doc = MedicationDocument(**sr.structured_data)
    # ... extract fields
```

The chat assembler in `router.py` follows the same dispatch. Each family produces a different context block format. The chat assembler differs from `context_block.py` in that it formats for Claude readability (plain text blocks with labels), not for embedding input.

### Anti-Patterns to Avoid

- **Modifying `context_block.py`:** This file is Phase 4 (embedding assembler) — do NOT change it. Create a separate chat assembler function in `router.py`.
- **LLM-generated SQL:** Never call `generate_json()` asking for raw SQL. Parameters only — inject into templates.
- **Raising from soft-fail paths:** Any SQL failure, any search failure, any interpreter failure must be caught and logged. Chat always responds.
- **`anthropic` SDK for router:** Installed but unused. All LLM calls go through `generate_json()` (Azure OpenAI). Do not introduce Anthropic SDK usage in Phase 5.
- **New directories:** No new directories. `router.py` goes directly in `services/rag/`.
- **Pydantic v1 patterns:** The project uses Pydantic 2.x. Use `model_dump()`, not `.dict()`. Use `BaseModel` from `pydantic`, not `pydantic.v1`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SQL user scoping | LLM-controlled WHERE clause | Supabase `.eq("user_id", user_id)` chained by code | LLM cannot be trusted to inject user_id — security boundary |
| JSON LLM calls | Raw `openai` client setup | `generate_json()` from `llm.py` | Already handles mock, truncation, deployment config |
| Supabase client | New client instantiation | `_get_client()` from `supabase_store.py` | Module-level singleton — avoids multiple connections |
| Token counting | External tokenizer library | Character approximation (~4 chars/token) | No tokenizer installed; character approx sufficient for budget enforcement |
| Structured output parsing | Custom JSON schema validation | Pydantic `RoutingResult(**json.loads(raw))` | Same pattern as all other structured outputs in the project |
| Abbreviation expansion | Regex-based NLP | Simple dict + `re.sub` word-boundary replacement | Five terms only; dict lookup is sufficient and robust |

---

## SQL Template Set (inferred from `patient_store.py` and `patient_observations` schema)

### Available Tables and Key Columns

From `patient_store.py` insertion patterns (verified):

**`patient_observations`**
- `user_id` (TEXT), `normalized_analyte` (TEXT), `raw_analyte` (TEXT)
- `value_str` (TEXT), `unit` (TEXT), `reference_range` (TEXT), `flag` (TEXT)
- `observed_date` (DATE), `needs_review` (BOOLEAN), `document_id` (TEXT)

**`patient_medications`**
- `user_id` (TEXT), `normalized_medication` (TEXT), `raw_medication` (TEXT)
- `dose` (TEXT), `route` (TEXT), `frequency` (TEXT), `status` (TEXT)
- `document_id` (TEXT)

**`patient_conditions`**
- `user_id` (TEXT), `normalized_condition` (TEXT), `raw_condition` (TEXT)
- `clinical_status` (TEXT — "active" | "suspected"), `verification_status` (TEXT)
- `document_id` (TEXT)

**`patient_allergies`**
- `user_id` (TEXT), `normalized_allergen` (TEXT), `raw_allergen` (TEXT)
- `reaction` (TEXT), `document_id` (TEXT)

**`patient_imaging_findings`**
- `user_id` (TEXT), `modality` (TEXT), `body_region` (TEXT)
- `impression` (TEXT), `urgency` (TEXT), `document_id` (TEXT)

### SQL Step Types (mapping `sql_steps` strings to query templates)

| Step Key | SQL Template | LLM-extracted params |
|----------|-------------|----------------------|
| `observations:{analyte}` | SELECT value_str, unit, flag, observed_date FROM patient_observations WHERE user_id=? AND normalized_analyte=? ORDER BY observed_date DESC LIMIT 10 | analyte name |
| `observations:{analyte}:range:{start}:{end}` | + AND observed_date BETWEEN ? AND ? | analyte, start_date, end_date |
| `medications:active` | SELECT raw_medication, dose, frequency FROM patient_medications WHERE user_id=? AND status='active' | none |
| `conditions:active` | SELECT raw_condition, clinical_status FROM patient_conditions WHERE user_id=? AND clinical_status='active' | none |
| `allergies:all` | SELECT raw_allergen, reaction FROM patient_allergies WHERE user_id=? | none |
| `imaging:recent` | SELECT modality, body_region, impression, urgency FROM patient_imaging_findings WHERE user_id=? ORDER BY id DESC LIMIT 5 | none |

**Note:** Supabase Python SDK uses method chaining (`.select().eq().order().limit().execute()`), not raw SQL strings. This is the validation/safety layer — no string interpolation, no injection risk.

---

## Context Assembly — Concrete Format

### Chat Context Block per Document (RETRIEVE-05)

The current `retriever.py` produces: `[Fonte: {r.source_name}]\n{r.excerpt}` where `r.excerpt` is a 400-500 char raw OCR string. The new assembler produces:

```
[Fonte: Hemograma Completo | structured_lab | 2024-01-15]
Summary: Suboptimal glycemic control. Recomenda-se seguimento endocrinológico.
Findings: HbA1c: 7.8% (ref: <5.7%) [high] | Glicose: 142 mg/dL [high] | Creatinina: 0.9 mg/dL [normal]
Entities: diabetes mellitus, hemoglobina glicada, controle glicêmico
```

The assembler reads from `SearchResult.doc_id` → needs the `structured_result` for that document. However, `SearchResult` (from `search.py`) only carries `doc_id`, `source_name`, `excerpt`, `score`. To access `structured_result`, the assembler must fetch it from Supabase (documents table) by `doc_id`.

**Implementation decision for planner:** The assembler can either (a) fetch `structured_result` per doc_id from Supabase in a second query, or (b) pass the `StructuredResult` alongside `SearchResult`. Option (a) adds Supabase round-trips. Option (b) requires storing structured_result during indexing. The cleanest approach given the existing architecture: fetch from `documents` table by doc_id after search (already has `_get_client()` available). This is a minor N+1 but acceptable for top_k=2-3.

**Fallback:** If structured_result is None or the fetch fails, fall back to the existing `r.excerpt` raw text format (soft-fail, never lose context).

### SQL Context Block Format (D-12)

```
=== DADOS ESTRUTURADOS DO PACIENTE ===
HbA1c (hemoglobina glicada): 7.8% [high] (2024-01-15), 7.1% [high] (2023-07-20), 6.8% (2023-01-10)
=== FIM DOS DADOS ESTRUTURADOS ===
```

### Updated SYSTEM_PROMPT (D-18/D-19)

The current `SYSTEM_PROMPT` has 6 rules. The update adds: instruct Claude to treat `=== DADOS ESTRUTURADOS ===` block as ground truth, use documents as supporting evidence, and synthesize across both. Existing rules (cite sources, never invent, never diagnose, Brazilian Portuguese) are preserved.

---

## Common Pitfalls

### Pitfall 1: `SearchResult` Does Not Carry `structured_result`

**What goes wrong:** The assembler tries to access `r.structured_result` on a `SearchResult` — that field does not exist. `SearchResult` only has `doc_id`, `source_name`, `excerpt`, `score`.
**Why it happens:** `SearchResult` is a dataclass for search scoring, not a document model.
**How to avoid:** Fetch `structured_result` from Supabase `documents` table using `doc_id` after search. Use `supabase_store._get_client().table("documents").select("structured_result").eq("id", doc_id).single().execute()`.
**Warning signs:** `AttributeError: 'SearchResult' object has no attribute 'structured_result'` at runtime.

### Pitfall 2: `RoutingResult` JSON Parse Failure in Mock Mode

**What goes wrong:** `generate_json()` returns `"{}"` in mock mode. `json.loads("{}")` succeeds but `RoutingResult(**{})` fails because `intent` is required and has no default.
**Why it happens:** `generate_json()` mock returns minimal empty JSON (verified in `llm.py` line 85).
**How to avoid:** In `route_query()`, the mock guard returns early before calling `generate_json()`. `if _use_mock(): return RoutingResult(intent="search_only", search_queries=[expanded_question])`.
**Warning signs:** `ValidationError: intent field required` when `USE_MOCK_AZURE=true`.

### Pitfall 3: Supabase Client Import Cycle

**What goes wrong:** `router.py` imports `_get_client` from `supabase_store` which imports from `models.document` — circular if `models.document` also imports from `services.*`.
**Why it happens:** The existing code already handles this by importing `_get_client` inside function bodies where needed (lazy import pattern).
**How to avoid:** Follow the pattern in `patient_store.py` line 49 — import `_get_client` at the top of the file (it works in the existing codebase, no circular import exists).
**Warning signs:** `ImportError: cannot import name '_get_client'` or `circular import` errors on startup.

### Pitfall 4: Token Budget Not Enforced

**What goes wrong:** SQL results for a patient with 5 years of HbA1c measurements produce a 2000-token block, leaving no budget for retrieved documents.
**Why it happens:** The Supabase query returns all matching rows if LIMIT is not set.
**How to avoid:** Always cap SQL queries with `.limit(10)` or fewer. Cap the formatted SQL block at ~800 characters (~200 tokens). Reduce search top_k from 3 to 2 when SQL block exists.
**Warning signs:** Claude context window warnings or truncated responses.

### Pitfall 5: Pydantic `tuple[date, date]` JSON Serialization

**What goes wrong:** `time_range: tuple[date, date] | None` fails JSON round-trip — `json.loads` returns a list, not a tuple, and date strings need parsing.
**Why it happens:** JSON has no tuple type; dates serialize as strings.
**How to avoid:** Define `time_range` as `list[str] | None` with ISO date strings, or use a nested Pydantic model. Parse dates in the SQL executor, not in the schema. The planner can decide: simplest approach is `time_range: list[str] | None` with ISO strings `["2024-01-01", "2024-12-31"]`.

### Pitfall 6: `normalized_analyte` vs. `raw_analyte`

**What goes wrong:** The LLM extracts "HbA1c" as the entity. The patient_observations table stores "hemoglobina glicada" as `normalized_analyte` (after alias normalization in Phase 2). Query for "HbA1c" finds nothing.
**Why it happens:** Phase 2 ran alias normalization (`_normalize_analyte()`) on all stored observations.
**How to avoid:** Abbreviation expansion (D-05) runs before the interpreter call. After expansion, "HbA1c" → "hemoglobina glicada" → LLM extracts "hemoglobina glicada" → SQL query matches `normalized_analyte`. Alternatively, query both `normalized_analyte` and `raw_analyte` with OR logic.
**Warning signs:** SQL returns 0 rows for analytes that definitely exist in the database.

---

## Code Examples

### Router Entry Point Skeleton

```python
# Source: derived from llm.py generate_json() + search.py _use_mock() + patient_store.py patterns
import json
import logging
import os
import re
from pydantic import BaseModel
from typing import Literal
from services.azure.llm import generate_json
from services.azure.search import search, SearchResult
from services.azure.embeddings import generate_embedding
from services.supabase_store import _get_client

logger = logging.getLogger(__name__)

_use_mock_cache: bool | None = None

def _use_mock() -> bool:
    global _use_mock_cache
    if _use_mock_cache is None:
        _use_mock_cache = os.getenv("USE_MOCK_AZURE", "true").lower() == "true"
    return _use_mock_cache

ABBREV_MAP = {
    "HbA1c": "hemoglobina glicada",
    "PA": "pressão arterial",
    "FC": "frequência cardíaca",
    "FR": "frequência respiratória",
    "SpO2": "saturação de oxigênio",
}

def expand_abbreviations(text: str) -> str:
    for abbrev, expansion in ABBREV_MAP.items():
        text = re.sub(rf'\b{re.escape(abbrev)}\b', expansion, text)
    return text

class RoutingResult(BaseModel):
    intent: Literal["sql_only", "search_only", "mixed"]
    entities: list[str] = []
    time_range: list[str] | None = None   # [ISO start, ISO end] or None
    sql_steps: list[str] = []
    search_queries: list[str] = []

def route_query(question: str, user_id: str) -> RoutingResult:
    if _use_mock():
        return RoutingResult(intent="search_only", search_queries=[question])
    expanded = expand_abbreviations(question)
    try:
        raw = generate_json(ROUTER_SYSTEM_PROMPT, expanded)
        data = json.loads(raw)
        return RoutingResult(**data)
    except Exception as e:
        logger.warning("route_query failed, fallback to search_only: %s", e)
        return RoutingResult(intent="search_only", search_queries=[expanded])
```

### Chat Context Assembler Skeleton

```python
# Source: pattern derived from context_block.py family dispatch
from models.document import StructuredResult, StructuredLab, ImagingReport, ClinicalNote, MedicationDocument

def assemble_chat_block(sr: StructuredResult | None, source_name: str, collection_date: str | None) -> str:
    """Assemble a compact clinical block for Claude's prompt (<300 tokens)."""
    header = f"[Fonte: {source_name} | {sr.document_family if sr else 'unknown'} | {collection_date or 'data desconhecida'}]"
    if sr is None:
        return header  # no structured data available

    parts = [header]
    try:
        if sr.document_family == "structured_lab":
            lab = StructuredLab(**sr.structured_data)
            if lab.summary:
                parts.append(f"Summary: {lab.summary}")
            if lab.findings:
                findings_str = " | ".join(
                    f"{f.name}: {f.value}{' ' + f.unit if f.unit else ''}{' [' + f.flag + ']' if f.flag else ''}"
                    for f in lab.findings[:10]  # cap at 10 findings
                )
                parts.append(f"Findings: {findings_str}")
        # ... other families follow context_block.py dispatch pattern
    except Exception:
        pass  # malformed structured_data — use header only

    block = "\n".join(parts)
    return block[:1200]  # ~300 tokens cap
```

### Refactored `build_context_prompt()` Skeleton

```python
# Source: replaces backend/services/rag/retriever.py build_context_prompt() internals
def build_context_prompt(question: str, user_id: str) -> tuple[str, list[str]]:
    """Signature unchanged — chat.py requires no modifications."""
    routing = route_query(question, user_id)

    sql_block = ""
    if routing.intent in ("sql_only", "mixed"):
        sql_block = _execute_sql_steps(routing.sql_steps, routing.time_range, user_id)

    search_block = ""
    sources = []
    if routing.intent in ("search_only", "mixed"):
        top_k = 2 if sql_block else 3
        for q in routing.search_queries or [question]:
            vec = generate_embedding(q)
            results = search(q, user_id, top_k=top_k, query_vector=vec)
            # ... assemble search_block from structured context blocks
            # ... append to sources

    context = _merge_context(sql_block, search_block)
    full_system = f"{SYSTEM_PROMPT}\n\n{context}"
    return full_system, sources
```

---

## State of the Art (Project-Specific)

| Old Approach (current) | New Approach (Phase 5) | Impact |
|------------------------|------------------------|--------|
| `r.excerpt` — raw OCR string, 400-500 chars | Structured clinical block: header + summary + findings | Claude receives lab values with units and flags, not OCR noise |
| No intent classification | LLM classifier: `sql_only` / `search_only` / `mixed` | Numeric questions answered from data, not document search |
| No SQL path | Supabase patient table queries via template+parameters | "Average HbA1c last year" returns a computed answer |
| `[Fonte: X]\n{excerpt}` flat format | Sectioned context with `=== DADOS ESTRUTURADOS ===` boundary | Claude knows which data is ground truth vs. supporting |
| No abbreviation handling | Pre-call expansion: HbA1c → hemoglobina glicada | LLM entity extraction works for Portuguese medical terms |

---

## Open Questions

1. **`StructuredResult` fetch after search** — The cleanest solution is to fetch `documents.structured_result` for each search result doc_id. This adds 2-3 Supabase round-trips per chat query. Alternative: extend `SearchResult` to carry `structured_result` and populate it during indexing. The planner should decide based on Phase 4's `index_document()` — it stores the context block text but not the full structured_result JSON. Round-trip fetch is safer and avoids schema changes.
   - What we know: `documents` table has `structured_result` JSONB column. `_get_client()` is available.
   - What's unclear: Whether the latency is acceptable for the chat streaming use case.
   - Recommendation: Use the fetch approach; add a try/except soft-fail with excerpt fallback.

2. **Router system prompt language** — Should the interpreter system prompt be in English or Portuguese? The LLM receives a Portuguese patient question. English prompts may produce better-structured JSON (LLM training data is English-dominant).
   - Recommendation: English system prompt for the router interpreter, since the output is JSON (not patient-facing). The patient question is passed as the user message.

3. **`time_range` in `RoutingResult`** — LLM must resolve "last year" to ISO dates. The router system prompt must include today's date for accurate resolution.
   - Recommendation: Inject `datetime.date.today().isoformat()` into the router system prompt string at call time, not as a constant.

---

## Environment Availability

Step 2.6: All dependencies are pure Python libraries already installed. No external CLI tools, databases (Supabase is accessed via API), or services beyond what Phase 4 already uses. No environment availability audit needed for new dependencies.

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `openai` (Python SDK) | `generate_json()` for router interpreter | Yes | `>=1.0.0` in requirements.txt | Mock mode (`_use_mock()`) |
| `supabase` (Python SDK) | SQL patient table queries | Yes | `2.4.6` | Mock mode (skip SQL steps) |
| `pydantic` | `RoutingResult` schema | Yes | `2.7.1` | N/A — required |
| Azure OpenAI deployment | LLM inference | Yes (via env vars) | gpt-4o-mini | Mock mode |

---

## Validation Architecture

`nyquist_validation` is enabled in `.planning/config.json`.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.2.0 |
| Config file | none (uses `conftest.py` at `backend/`) |
| Quick run command | `cd backend && python -m pytest tests/rag/test_router.py -x -q` |
| Full suite command | `cd backend && python -m pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| RETRIEVE-04 | `route_query()` returns `sql_only` for aggregation queries | unit | `pytest tests/rag/test_router.py::test_route_aggregation_returns_sql_only -x` | Wave 0 |
| RETRIEVE-04 | `route_query()` returns `search_only` for narrative queries | unit | `pytest tests/rag/test_router.py::test_route_narrative_returns_search_only -x` | Wave 0 |
| RETRIEVE-04 | `route_query()` returns `mixed` for mixed queries | unit | `pytest tests/rag/test_router.py::test_route_mixed_intent -x` | Wave 0 |
| RETRIEVE-04 | `route_query()` falls back to `search_only` on LLM failure | unit | `pytest tests/rag/test_router.py::test_route_fallback_on_llm_failure -x` | Wave 0 |
| RETRIEVE-04 | `route_query()` returns `search_only` in mock mode | unit | `pytest tests/rag/test_router.py::test_route_mock_mode -x` | Wave 0 |
| RETRIEVE-04 | SQL executor queries `patient_observations` with `user_id` scoped | unit | `pytest tests/rag/test_router.py::test_sql_observations_scoped_by_user_id -x` | Wave 0 |
| RETRIEVE-04 | SQL executor rejects results from wrong user | unit | `pytest tests/rag/test_router.py::test_sql_user_isolation -x` | Wave 0 |
| RETRIEVE-04 | `expand_abbreviations()` expands all 5 terms | unit | `pytest tests/rag/test_router.py::test_expand_abbreviations -x` | Wave 0 |
| RETRIEVE-05 | `assemble_chat_block()` produces structured lab block | unit | `pytest tests/rag/test_router.py::test_chat_block_structured_lab -x` | Wave 0 |
| RETRIEVE-05 | `assemble_chat_block()` falls back to excerpt when `sr` is None | unit | `pytest tests/rag/test_router.py::test_chat_block_fallback -x` | Wave 0 |
| RETRIEVE-05 | `build_context_prompt()` includes `=== DADOS ESTRUTURADOS ===` section when SQL path taken | unit | `pytest tests/rag/test_retriever.py::test_context_includes_sql_section -x` | Wave 0 |
| RETRIEVE-05 | `build_context_prompt()` signature unchanged — returns `tuple[str, list[str]]` | unit | `pytest tests/rag/test_retriever.py -x` | Partially exists (existing 3 tests) |

### Sampling Rate

- **Per task commit:** `cd backend && python -m pytest tests/rag/ -q`
- **Per wave merge:** `cd backend && python -m pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `backend/tests/rag/test_router.py` — covers RETRIEVE-04 and RETRIEVE-05 (all test cases above)
- [ ] No framework gaps — existing `conftest.py` at `backend/` already sets up sys.path

**Existing tests that must remain green:**
- `backend/tests/rag/test_retriever.py` — 3 tests for `build_context_prompt()`. Must remain green after refactor.
- `backend/tests/rag/test_context_block.py` — 7 tests for `assemble_context_block()`. Must remain green (`context_block.py` is read-only).

---

## Sources

### Primary (HIGH confidence)
- `backend/services/rag/retriever.py` — exact current `build_context_prompt()` implementation (51 lines)
- `backend/services/azure/llm.py` — `generate_json()` and `chat_stream()` patterns; confirmed Azure OpenAI only
- `backend/services/azure/search.py` — `_use_mock()` mock guard pattern; `SearchResult` dataclass fields
- `backend/services/azure/embeddings.py` — `generate_embedding()` soft-fail and mock guard
- `backend/services/patient_store.py` — Supabase client pattern; all 5 patient table schemas inferred from insertion code
- `backend/services/rag/context_block.py` — family dispatch pattern; Phase 4 assembler (read-only)
- `backend/models/document.py` — `StructuredLab`, `LabFinding`, `ImagingReport`, `ClinicalNote`, `MedicationDocument`, `StructuredResult` full schemas
- `backend/api/chat.py` — exact call to `build_context_prompt()` confirming signature must be preserved
- `backend/requirements.txt` — confirmed library versions; `instructor` NOT installed; `anthropic==0.28.0` installed but unused by any service

### Secondary (MEDIUM confidence)
- `.planning/phases/05-query-routing-and-context-assembly/05-CONTEXT.md` — user decisions, SQL allowlist, context budget
- `.planning/research/retrieval.md` — query routing architecture and context assembly patterns (prior research)

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — verified from requirements.txt and existing service files
- Architecture patterns: HIGH — derived directly from existing code, not assumptions
- SQL table schemas: HIGH — inferred from insertion patterns in patient_store.py (actual column names confirmed)
- Pitfalls: HIGH — identified from code inspection and known Python/Supabase SDK behaviors
- Test map: HIGH — follows established test patterns from Phase 4

**Research date:** 2026-04-08
**Valid until:** 2026-05-08 (stable stack, no fast-moving dependencies)

---

## RESEARCH COMPLETE
