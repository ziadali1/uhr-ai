---
phase: 4
slug: hybrid-search-index
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-06
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.2.0 (installed) |
| **Config file** | None — tests use `sys.path.insert` pattern |
| **Quick run command** | `cd backend && python -m pytest tests/rag/ -x -q` |
| **Full suite command** | `cd backend && python -m pytest tests/ -x -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && python -m pytest tests/rag/ -x -q`
- **After every plan wave:** Run `cd backend && python -m pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 4-01-01 | 01 | 1 | RETRIEVE-01 | manual | Azure Portal tier check | N/A | ⬜ pending |
| 4-02-01 | 02 | 1 | RETRIEVE-01 | unit | `pytest tests/rag/test_search_schema.py -x` | ❌ W0 | ⬜ pending |
| 4-03-01 | 03 | 1 | RETRIEVE-02 | unit | `pytest tests/rag/test_context_block.py -x` | ❌ W0 | ⬜ pending |
| 4-03-02 | 03 | 1 | RETRIEVE-02 | unit | `pytest tests/rag/test_embeddings.py -x` | ❌ W0 | ⬜ pending |
| 4-04-01 | 04 | 2 | RETRIEVE-02 | unit | `pytest tests/rag/test_indexer.py -x` | ❌ W0 | ⬜ pending |
| 4-05-01 | 05 | 2 | RETRIEVE-03 | unit | `pytest tests/rag/test_retriever.py -x` | ❌ W0 | ⬜ pending |
| 4-06-01 | 06 | 3 | RETRIEVE-01,02,03 | smoke | `cd backend && python -m pytest tests/ -x -q` | Partially | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/rag/test_search_schema.py` — stubs for RETRIEVE-01 (index schema construction)
- [ ] `tests/rag/test_context_block.py` — stubs for RETRIEVE-02 (context block assembly per family)
- [ ] `tests/rag/test_embeddings.py` — stubs for RETRIEVE-02 (generate_embedding unit tests)
- [ ] `tests/rag/test_indexer.py` — stubs for RETRIEVE-02 (indexer calls embedding, passes vector)
- [ ] `tests/rag/test_retriever.py` — stubs for RETRIEVE-03 (retriever uses VectorizedQuery)
- [ ] `tests/rag/__init__.py` — if missing, add for test discovery

*Plan 01 (Wave 1) creates all Wave 0 test stubs before implementation begins.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Hybrid query returns more relevant results than BM25 on 10 sample clinical queries | RETRIEVE-03 | Requires live Azure AI Search + real clinical documents | Upload 10 test documents; run queries; compare results qualitatively vs BM25 baseline |
| Azure AI Search tier verified | RETRIEVE-01 | Azure Portal check | Navigate to Search service → Overview → Pricing tier; confirm S1 or higher |
| Azure OpenAI embedding deployment provisioned | RETRIEVE-02 | Azure Portal action | Navigate to Azure OpenAI → Deployments; confirm `text-embedding-3-small` deployment exists |
| All existing documents re-indexed with vectors | RETRIEVE-01 | Requires live Azure query | Run re-index script; query index for `content_vector` field presence on a sample document |
| No regression in existing chat functionality | All | End-to-end smoke | Send 5 chat messages post-retriever update; confirm responses cite correct documents |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING test file references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
