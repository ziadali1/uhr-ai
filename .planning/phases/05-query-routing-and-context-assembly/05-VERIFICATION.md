---
phase: 05-query-routing-and-context-assembly
verified: 2026-04-08T00:00:00Z
status: passed
score: 15/15 must-haves verified
re_verification: false
---

# Phase 05: Query Routing and Context Assembly — Verification Report

**Phase Goal:** Implement query routing and context assembly — route_query(), execute_sql_steps(), assemble_chat_block() wired into retriever, SYSTEM_PROMPT updated per D-18/D-19
**Verified:** 2026-04-08
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `route_query()` returns a RoutingResult Pydantic model for any input | VERIFIED | `class RoutingResult(BaseModel)` at router.py:61; mock mode path tested and passing |
| 2 | Abbreviation expansion runs before the LLM call (HbA1c → hemoglobina glicada) | VERIFIED | `expand_abbreviations()` called at router.py:108 (mock) and 111 (live) before `generate_json()`; test_expand_abbreviations PASSED |
| 3 | Mock mode returns search_only without calling generate_json() | VERIFIED | `if _use_mock():` guard at router.py:107 returns early; test_route_mock_mode asserts `mock_gen.call_count == 0` — PASSED |
| 4 | LLM failure falls back to search_only with the original question | VERIFIED | `except Exception` at router.py:119 returns `RoutingResult(intent="search_only", ...)`; test_route_fallback_on_llm_failure PASSED |
| 5 | SQL executor functions scope every query with user_id injected by code | VERIFIED | `.eq("user_id", user_id)` appears 6 times across all 5 patient tables; test_sql_user_isolation PASSED |
| 6 | SQL mutations (INSERT/UPDATE/DELETE) are never possible via template pattern | VERIFIED | No raw SQL string interpolation found; all queries use read-only Supabase SDK `.select()` chains only |
| 7 | assemble_chat_block() produces a compact clinical block per document | VERIFIED | Full family dispatch (structured_lab, imaging_narrative, clinical_narrative, medication_document) at router.py:357-408; test_chat_block_structured_lab PASSED |
| 8 | When structured_result is None or fetch fails, fallback returns raw excerpt | VERIFIED | router.py:351-352 returns `f"{header}\n{excerpt[:400]}"` when sr is None; test_chat_block_fallback PASSED |
| 9 | assemble_chat_block fetches structured_result from documents table by doc_id | VERIFIED | `_fetch_structured_result()` at router.py:324-335 queries `client.table("documents").select("structured_result").eq("id", doc_id)` |
| 10 | Block output begins with [Fonte: source \| family \| date] header | VERIFIED | `header = f"[Fonte: {source_name} \| {family} \| {date_str}]"` at router.py:349; all test paths confirmed |
| 11 | build_context_prompt() calls route_query() as first step | VERIFIED | retriever.py:41 `routing = route_query(question, user_id)` is Step 1 |
| 12 | SQL results appear before retrieved documents in the final context | VERIFIED | retriever.py:70-71 appends sql_block first, then docs_section at 83-88 |
| 13 | Retrieved documents are formatted via assemble_chat_block(), not raw excerpt | VERIFIED | retriever.py:76-81 calls `assemble_chat_block(doc_id=r.doc_id, ...)` for every SearchResult |
| 14 | SYSTEM_PROMPT instructs Claude to treat === DADOS ESTRUTURADOS === as ground truth (D-18) | VERIFIED | retriever.py:28 `Trate-os como fonte primária de verdade.`; D-19 synthesis rule at line 30 |
| 15 | api/chat.py requires zero changes — build_context_prompt signature preserved | VERIFIED | retriever.py:33 `def build_context_prompt(question: str, user_id: str) -> tuple[str, list[str]]:`; api/chat.py:31 `system_prompt, sources = build_context_prompt(request.message, user_id)` — unchanged |

**Score: 15/15 truths verified**

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/services/rag/router.py` | RoutingResult, expand_abbreviations(), route_query(), execute_sql_steps(), _execute_single_step(), format_sql_block(), _fetch_structured_result(), assemble_chat_block() | VERIFIED | 420 lines; all 8 exports present; substantive implementation confirmed |
| `backend/services/rag/retriever.py` | Refactored build_context_prompt() with router integration, updated SYSTEM_PROMPT | VERIFIED | 97 lines; imports route_query, execute_sql_steps, format_sql_block, assemble_chat_block; SYSTEM_PROMPT contains D-18/D-19 instructions |
| `backend/tests/rag/test_router.py` | 11 implemented test cases, no skips remaining | VERIFIED | 178 lines; 0 `@pytest.mark.skip` decorators; all 11 tests PASSED |
| `backend/tests/rag/test_retriever.py` | test_context_includes_sql_section implemented + 3 original tests green | VERIFIED | 89 lines; 0 `@pytest.mark.skip` decorators; 4/4 tests PASSED |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `retriever.py build_context_prompt()` | `services.rag.router.route_query` | `from services.rag.router import route_query` (line 13) + called at line 41 | WIRED | Import confirmed at line 13; call at line 41 |
| `retriever.py build_context_prompt()` | `services.rag.router.assemble_chat_block` | imported line 17, called line 76 per search result | WIRED | Import block lines 13-18; used in search_results loop |
| `retriever.py build_context_prompt()` | `services.rag.router.execute_sql_steps` | imported line 15, called line 46 for sql_only/mixed | WIRED | Conditioned on `routing.intent in ("sql_only", "mixed") and routing.sql_steps` |
| `router.py route_query()` | `services.azure.llm.generate_json` | `from services.azure.llm import generate_json` (line 15) + called at line 114 | WIRED | Import confirmed; only called when not in mock mode |
| `router.py SQL executors` | `services.supabase_store._get_client` | `from services.supabase_store import _get_client` (line 18) + called at line 154 in `_execute_single_step` and line 327 in `_fetch_structured_result` | WIRED | Both executors call `_get_client()` at function entry |
| `router.py assemble_chat_block()` | `supabase documents table` | `_fetch_structured_result()` → `client.table("documents").select("structured_result").eq("id", doc_id).single().execute()` at line 328 | WIRED | Documents table query confirmed |
| `test_router.py` | `services.rag.router` | `from services.rag.router import ...` at line 8 (module-level, module now exists) | WIRED | Direct module-level import; all 6 exports confirmed |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `retriever.py build_context_prompt()` | `routing` | `route_query()` → LLM `generate_json()` or mock | Yes (or mock fallback) | FLOWING |
| `retriever.py build_context_prompt()` | `sql_block` | `execute_sql_steps()` → Supabase SDK `.execute()` on patient tables | Yes — SDK queries 5 patient tables | FLOWING |
| `retriever.py build_context_prompt()` | `search_results` | `search()` Azure AI Search via `generate_embedding()` + hybrid search | Yes — hybrid vector+keyword | FLOWING |
| `retriever.py build_context_prompt()` | context assembly | `assemble_chat_block()` → `_fetch_structured_result()` → Supabase documents table | Yes — or excerpt fallback | FLOWING |

All data paths have real sources. No hardcoded empty returns in production paths.

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full RAG test suite | `python -m pytest tests/rag/ -v -q` | 28 passed, 5 skipped (test_search_schema pre-existing skips), 0 failed in 1.02s | PASS |
| 11 router tests all pass | `python -m pytest tests/rag/test_router.py -v` | 11 passed, 0 skipped, 0 failed | PASS |
| 4 retriever tests all pass | `python -m pytest tests/rag/test_retriever.py -v` | 4 passed, 0 skipped, 0 failed | PASS |
| No skip decorators remain in test_router.py | `grep -c @pytest.mark.skip test_router.py` | 0 matches | PASS |
| No skip decorators remain in test_retriever.py | `grep -c @pytest.mark.skip test_retriever.py` | 0 matches | PASS |
| user_id injected 6 times in router (all 5 patient tables + observations:range) | `grep -c .eq("user_id"` | 6 occurrences | PASS |
| No raw SQL string interpolation | `grep f"SELECT\|f"WHERE` | 0 matches | PASS |
| api/chat.py call site unchanged | `grep build_context_prompt api/chat.py` | Line 31: `system_prompt, sources = build_context_prompt(request.message, user_id)` | PASS |

---

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
|-------------|---------------|-------------|--------|---------|
| RETRIEVE-04 | 05-01, 05-02, 05-04, 05-05 | System classifies query intent and routes numeric/aggregation queries to Supabase SQL, narrative queries to Azure AI Search | SATISFIED | `route_query()` classifies intent (sql_only/search_only/mixed); `execute_sql_steps()` runs Supabase queries; retriever wires both paths; 7 router tests cover routing behavior |
| RETRIEVE-05 | 05-01, 05-03, 05-04, 05-05 | Context injected into Claude uses structured entity blocks (lab values, flags, summaries) not 500-char raw text truncations | SATISFIED | `assemble_chat_block()` produces D-11 format with Summary/Findings/Entities sections; `_fetch_structured_result()` fetches from documents table; retriever calls assembler per search result; test_chat_block_structured_lab and test_context_includes_sql_section confirm end-to-end |

Both RETRIEVE-04 and RETRIEVE-05 marked `[x]` (complete) in REQUIREMENTS.md traceability table. No orphaned requirements for Phase 5 found.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None | — | — | — | — |

No TODO/FIXME/placeholder comments, no empty handlers, no hardcoded empty returns in production code paths. The 5 skipped tests in `test_search_schema.py` are pre-existing Phase 4 skips unrelated to Phase 5.

---

### Human Verification Required

None. All phase 5 behaviors are programmatically verifiable and confirmed by the test suite.

---

### Gaps Summary

No gaps. All must-haves verified, all artifacts substantive and wired, all data paths flowing, all 15 tests passing, requirements RETRIEVE-04 and RETRIEVE-05 fully satisfied.

---

_Verified: 2026-04-08_
_Verifier: Claude (gsd-verifier)_
