# Phase 5: Query Routing and Context Assembly — Context

**Gathered:** 2026-04-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Replace the current flat `build_context_prompt(question, user_id)` pipeline with an LLM-driven query routing and context assembly layer. This phase ships:

- `services/rag/router.py` — LLM-based query interpreter: classifies intent, extracts entities, resolves temporal references, decides whether the question needs SQL, hybrid search, or both
- SQL query handlers for structured intents: observation trends, active medications, current conditions — with a lightweight validation/safety layer before execution
- Structured chat context assembler: formats patient-level facts + retrieved documents into compact clinical blocks for Claude's prompt
- Refactored `api/chat.py` / `services/rag/retriever.py` to use the router as entry point, merging SQL + search results into unified context
- Portuguese medical abbreviation expansion (HbA1c, PA, FC, FR, SpO2) — pre-processing before query interpretation

This phase does NOT include: frontend timeline views (Phase 6), clinical reasoning/differentials (Phase 7), security hardening (Phase 8). The goal is better retrieval and context quality inside the existing chat endpoint.

</domain>

<decisions>
## Implementation Decisions

### Query Interpretation Architecture

- **D-01:** Use the LLM as the **primary query interpreter** — a single LLM call that: classifies intent (`sql_only` | `search_only` | `mixed`), extracts entities (analyte names, medications, conditions, date ranges), resolves temporal references ("last year" → ISO date range), decides tool usage (which retrieval tools to invoke and with what parameters), and emits a structured routing plan.
- **D-02:** The interpreter produces a structured output (Pydantic model or JSON): intent type, extracted entities, time range if relevant, sub-questions if mixed intent.
- **D-03:** No regex/keyword fallback for primary classification. The LLM interpreter IS the router. Keep it simple — one call, structured output.
- **D-04:** On interpreter failure (LLM error, schema parse failure): fall back to `search_only` with the original query. Soft-fail — chat always responds.
- **D-05:** Portuguese abbreviation expansion happens **before** the interpreter call: expand HbA1c → "hemoglobina glicada", PA → "pressão arterial", FC → "frequência cardíaca", FR → "frequência respiratória", SpO2 → "saturação de oxigênio". This improves LLM entity extraction accuracy.

### SQL Generation

- **D-06:** LLM-assisted SQL generation for `sql_only` and `mixed` intents. The interpreter call (D-01) can optionally produce a SQL template or the intent type is mapped to a set of pre-approved query templates with LLM-extracted parameters filled in. **Preferred approach:** LLM extracts parameters (analyte name, date range, user_id already scoped), which are injected into safe query templates — hybrid between template safety and LLM flexibility.
- **D-07:** Lightweight validation layer before any SQL execution:
  - Verify table and field names are in the allowlist (`patient_observations`, `patient_conditions`, `patient_medications`, `patient_allergies`, `patient_imaging_findings`)
  - Enforce `user_id = {current_user_id}` scope is present on every query (injected by code, not LLM)
  - Reject queries with mutations (INSERT/UPDATE/DELETE/DROP — case-insensitive check)
  - Log every generated + validated query at DEBUG level
- **D-08:** SQL queries target the patient tables from Phase 2/3 — not the raw `documents` table. Supported query types: observation trends (aggregation by analyte + date), active medications (filter by status), current conditions (filter by clinical_status='active'), recent imaging findings.
- **D-09:** SQL failures soft-fail: if the query fails, log the error and continue with either (a) `search_only` retrieval using the original question, or (b) hybrid context with whatever partial structured data was retrieved before the failure. The fallback mode is chosen based on how much data was recovered — if partial SQL results are meaningful, include them alongside search results rather than discarding entirely.

### Context Assembly (Chat Context)

- **D-10:** Replace the current `[Fonte: X]\n{excerpt}` pattern (raw OCR) with a **structured clinical context block** per document. This is separate from `context_block.py` which is for embeddings (Phase 4) — the chat assembler formats for human-readable clinical reasoning, not embedding.
- **D-11:** Chat context block structure (per document, max ~300 tokens):
  ```
  [Fonte: {source_name} | {document_family} | {collection_date}]
  Summary: {summary if available}
  Findings: {lab values with units and flags, or impression/findings for imaging}
  Entities: {key clinical entities}
  ```
  Plain text, compact. No JSON in the prompt.
- **D-12:** Patient-level SQL results come **first** in the context block, before retrieved documents, and are treated as **ground truth facts** (structured, verified patient data takes precedence over document excerpts). SQL results are formatted as compact fact tables:
  ```
  === DADOS ESTRUTURADOS DO PACIENTE ===
  HbA1c: 6.2% (2024-01-15), 6.8% (2023-09-10), 7.1% (2023-03-05)
  === FIM DOS DADOS ESTRUTURADOS ===
  ```
- **D-13:** Retrieved documents follow SQL data as supporting context:
  ```
  === DOCUMENTOS DE SUPORTE ===
  [Fonte: ...] ...
  === FIM DOS DOCUMENTOS ===
  ```
- **D-14:** Total context budget: ~2000 tokens for SQL data + retrieved documents combined. If SQL result is large, reduce top-k for search from 3 to 2.

### Mixed Intent / LLM Planner

- **D-15:** For `mixed` intent: the interpreter (D-01/D-02) decomposes the question into sub-steps (e.g., "get HbA1c trend via SQL" + "retrieve endocrinology visit notes via search"). Each step is executed independently, results merged.
- **D-16:** Result synthesis for mixed intent: both SQL data and retrieved documents are passed to Claude in the same prompt (D-12/D-13 ordering). **Single synthesis call by default** — Claude reasons over the unified context and synthesizes the answer. A second dedicated synthesis call (e.g., for multi-step clinical reasoning) is explicitly deferred to a future extension; do not implement in Phase 5.
- **D-17:** The router is designed as a **tool-using clinical reasoning agent** — flexibility and diagnostic capability over production-grade template rigidity. This is a prototype/research project.

### System Prompt Updates

- **D-18:** Update the Claude system prompt (`SYSTEM_PROMPT` in `retriever.py`) to reflect the new context structure: instruct Claude to reason over structured patient data first, use retrieved documents as supporting evidence, and synthesize across both.
- **D-19:** Existing rules are kept: cite sources, never invent, never diagnose, respond in Brazilian Portuguese.

### Claude's Discretion

- LLM model used for the query interpreter (follow existing patterns — Azure OpenAI or Anthropic Claude as used elsewhere in the codebase)
- Exact Pydantic schema for the router's structured output
- Whether the router and assembler are separate files or combined in `services/rag/router.py`
- Token counting approach (character approximation is fine — no need for a tokenizer library)
- Exact SQL template set (infer from `patient_observations` schema + Phase 2 context)
- Whether the abbreviation expansion is a dict lookup or a small pre-processing function

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Current RAG implementation (files being replaced/extended)
- `backend/services/rag/retriever.py` — Current `build_context_prompt()` implementation: hybrid search, raw OCR context injection, system prompt. This is the primary file being refactored.
- `backend/api/chat.py` — Current chat endpoint: calls `build_context_prompt()`, streams SSE. Integration point for router.
- `backend/services/rag/context_block.py` — Phase 4 embedding assembler. Read for reference on structured_result field access patterns — do NOT modify this file.

### Patient tables (SQL target for structured intents)
- `backend/services/patient_store.py` — Promotion functions per document family. Read for table schema, field names, Supabase client pattern.
- `backend/models/document.py` — `StructuredLab`, `LabFinding`, `ImagingReport`, `ClinicalNote`, `MedicationDocument` — source models for context block assembly.

### Existing Azure/LLM services (patterns to follow)
- `backend/services/azure/search.py` — `search()` with hybrid query and mock guard pattern.
- `backend/services/azure/embeddings.py` — `generate_embedding()` pattern: try/except soft-fail, mock guard.
- `backend/services/azure/llm.py` — Existing LLM call pattern (if applicable for router interpreter call).

### Requirements for this phase
- `.planning/REQUIREMENTS.md` §Retrieval — RETRIEVE-04 (query routing), RETRIEVE-05 (structured context)
- `.planning/ROADMAP.md` §Phase 5 — Done-when criteria and plan breakdown

### Prior phase context (patterns to replicate)
- `.planning/phases/04-hybrid-search-index/04-CONTEXT.md` — D-10/D-23/D-24: mock mode handling, soft-fail embedding pattern
- `.planning/phases/02-longitudinal-patient-data-model/02-CONTEXT.md` — D-04/D-06/D-07: soft-fail promotion pattern

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `retriever.py` → `SYSTEM_PROMPT` constant: extend (not replace) with instructions for reasoning over structured data
- `retriever.py` → `build_context_prompt()`: replace internals, keep the function signature unchanged so `chat.py` requires minimal changes
- `context_block.py` → family dispatch pattern (structured_lab/imaging_narrative/clinical_narrative/medication_document): reuse for chat context assembler
- `patient_store.py` → `_get_client()` singleton: reuse for SQL query execution
- `search.py` → `_use_mock()` + mock guard: replicate in router for test/local mode

### Established Patterns
- Soft-fail: `try/except Exception as e: logger.warning(...); <fallback>` — never raise from optional steps
- Mock guard: `if _use_mock(): return <mock_result>` at function entry
- Module-level singletons for clients
- Pydantic 2.x models for all structured outputs

### Integration Points
- `backend/services/rag/router.py` — new file: `route_query(question, user_id) -> RoutingResult` (Pydantic)
- `backend/services/rag/retriever.py` — `build_context_prompt()` refactored to call `route_query()` then assemble context
- `backend/api/chat.py` — no changes needed if `build_context_prompt()` signature is preserved
- `backend/services/rag/context_block.py` — read-only reference; do NOT modify

</code_context>

<specifics>
## Specific Ideas

- **Abbreviation dict**: `{"HbA1c": "hemoglobina glicada", "PA": "pressão arterial", "FC": "frequência cardíaca", "FR": "frequência respiratória", "SpO2": "saturação de oxigênio"}` — simple word-boundary replacement before the interpreter call.
- **Router structured output schema**: `RoutingResult(intent: Literal["sql_only","search_only","mixed"], entities: list[str], time_range: tuple[date,date] | None, sql_steps: list[str] | None, search_queries: list[str])` — exact fields up to planner.
- **SQL allowlist**: `["patient_observations", "patient_conditions", "patient_medications", "patient_allergies", "patient_imaging_findings"]` — hardcoded in the validation layer.
- **user_id injection**: code always appends `.eq("user_id", user_id)` or equivalent WHERE clause — LLM never controls user scoping.
- **Context budget**: SQL block capped at ~800 tokens, search block at ~1200 tokens, total ~2000 tokens before Claude's own reasoning.
- **Mock mode**: in mock mode, router returns `search_only` intent without calling LLM, delegating to existing mock search. No SQL calls in mock mode.

</specifics>

<deferred>
## Deferred Ideas

- Multi-turn context memory (remembering previous questions in session) — post-Phase 5 optimization
- Full natural language to SQL via unconstrained LLM generation — Phase 5 uses template+LLM-parameter hybrid for safety; pure NL→SQL is a future option once validation is mature
- Semantic caching of router results — future optimization
- Citation linking (document ID → specific page) — Phase 6 or later
- Re-ranking SQL results by clinical relevance — future

</deferred>

---

*Phase: 05-query-routing-and-context-assembly*
*Context gathered: 2026-04-08*
