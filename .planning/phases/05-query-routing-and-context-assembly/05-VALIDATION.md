---
phase: 5
slug: query-routing-and-context-assembly
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-08
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.2.0 |
| **Config file** | `backend/conftest.py` (sys.path setup — already exists from Phase 4) |
| **Quick run command** | `cd backend && python -m pytest tests/rag/test_router.py -x -q` |
| **Full suite command** | `cd backend && python -m pytest tests/ -q` |
| **Estimated runtime** | ~10 seconds (unit tests only, no external calls) |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && python -m pytest tests/rag/ -q`
- **After every plan wave:** Run `cd backend && python -m pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 05-01-01 | 01 | 0 | RETRIEVE-04, RETRIEVE-05 | unit stubs | `pytest tests/rag/test_router.py -x -q` | ❌ W0 | ⬜ pending |
| 05-02-01 | 02 | 1 | RETRIEVE-04 | unit | `pytest tests/rag/test_router.py::test_route_aggregation_returns_sql_only -x` | ❌ W0 | ⬜ pending |
| 05-02-02 | 02 | 1 | RETRIEVE-04 | unit | `pytest tests/rag/test_router.py::test_route_narrative_returns_search_only -x` | ❌ W0 | ⬜ pending |
| 05-02-03 | 02 | 1 | RETRIEVE-04 | unit | `pytest tests/rag/test_router.py::test_route_mixed_intent -x` | ❌ W0 | ⬜ pending |
| 05-02-04 | 02 | 1 | RETRIEVE-04 | unit | `pytest tests/rag/test_router.py::test_route_fallback_on_llm_failure -x` | ❌ W0 | ⬜ pending |
| 05-02-05 | 02 | 1 | RETRIEVE-04 | unit | `pytest tests/rag/test_router.py::test_route_mock_mode -x` | ❌ W0 | ⬜ pending |
| 05-02-06 | 02 | 1 | RETRIEVE-04 | unit | `pytest tests/rag/test_router.py::test_expand_abbreviations -x` | ❌ W0 | ⬜ pending |
| 05-03-01 | 03 | 1 | RETRIEVE-04 | unit | `pytest tests/rag/test_router.py::test_sql_observations_scoped_by_user_id -x` | ❌ W0 | ⬜ pending |
| 05-03-02 | 03 | 1 | RETRIEVE-04 | unit | `pytest tests/rag/test_router.py::test_sql_user_isolation -x` | ❌ W0 | ⬜ pending |
| 05-04-01 | 04 | 1 | RETRIEVE-05 | unit | `pytest tests/rag/test_router.py::test_chat_block_structured_lab -x` | ❌ W0 | ⬜ pending |
| 05-04-02 | 04 | 1 | RETRIEVE-05 | unit | `pytest tests/rag/test_router.py::test_chat_block_fallback -x` | ❌ W0 | ⬜ pending |
| 05-05-01 | 05 | 2 | RETRIEVE-04, RETRIEVE-05 | unit | `pytest tests/rag/test_retriever.py -x` | ✅ exists | ⬜ pending |
| 05-05-02 | 05 | 2 | RETRIEVE-05 | unit | `pytest tests/rag/test_retriever.py::test_context_includes_sql_section -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/rag/test_router.py` — stubs for all RETRIEVE-04 and RETRIEVE-05 test cases (11 stubs, all `@pytest.mark.skip`)
- [ ] `backend/tests/rag/test_retriever.py::test_context_includes_sql_section` — new stub added to existing file

**Existing infrastructure covers framework setup:** `backend/conftest.py` already exists (added in Phase 4). No framework install needed.

**Existing tests that must remain green throughout Phase 5:**
- `backend/tests/rag/test_retriever.py` — 3 existing tests for `build_context_prompt()`. Must remain green after refactor.
- `backend/tests/rag/test_context_block.py` — 7 existing tests for `assemble_context_block()`. Must remain green (`context_block.py` is read-only in Phase 5).

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| "O que foi meu HbA1c médio no ano passado?" → SQL-computed answer | RETRIEVE-04 | Requires live Azure OpenAI + real patient data | Ask question in chat UI; verify answer cites specific HbA1c values from SQL, not document excerpts |
| Context block shows lab values with units and flags, not OCR fragments | RETRIEVE-05 | Output format requires visual inspection | Enable DEBUG logging; check context block in logs for `Findings:` format with units |
| "O que meu cardiologista disse?" → hybrid search response | RETRIEVE-04 | Requires live search index with real documents | Ask in chat; verify response draws from clinical note documents, not SQL |
| Mixed intent: "Minhas últimas medicações e o que meu cardiologista disse sobre elas?" | RETRIEVE-04 | Mixed path requires both SQL + search live | Verify response contains both structured medication data and document excerpts |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
