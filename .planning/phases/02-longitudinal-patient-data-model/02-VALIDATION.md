---
phase: 2
slug: longitudinal-patient-data-model
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-05
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.2.0 |
| **Config file** | none — tests discovered by default |
| **Quick run command** | `cd backend && python -m pytest tests/patient/ -x` |
| **Full suite command** | `cd backend && python -m pytest tests/ -v` |
| **Estimated runtime** | ~2 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && python -m pytest tests/patient/ -x`
- **After every plan wave:** Run `cd backend && python -m pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 2-01-01 | 01 (migration) | 1 | STORE-01 | manual | N/A — apply SQL to Supabase | ❌ W0 | ⬜ pending |
| 2-02-01 | 02 (aliases) | 1 | STORE-01 | manual | N/A — apply SQL to Supabase | ❌ W0 | ⬜ pending |
| 2-03-01 | 03 (patient_store) | 2 | STORE-02 | unit | `cd backend && python -m pytest tests/patient/test_patient_store.py -x` | ❌ W0 | ⬜ pending |
| 2-03-02 | 03 (patient_store) | 2 | STORE-02 | unit | same | ❌ W0 | ⬜ pending |
| 2-03-03 | 03 (patient_store) | 2 | STORE-02 | unit | same | ❌ W0 | ⬜ pending |
| 2-03-04 | 03 (patient_store) | 2 | STORE-03 | unit | same | ❌ W0 | ⬜ pending |
| 2-03-05 | 03 (patient_store) | 2 | STORE-03 | unit | same | ❌ W0 | ⬜ pending |
| 2-03-06 | 03 (patient_store) | 2 | STORE-03 | unit | same | ❌ W0 | ⬜ pending |
| 2-04-01 | 04 (upload wiring) | 3 | STORE-02 | unit | `cd backend && python -m pytest tests/patient/ -x` | ❌ W0 | ⬜ pending |
| 2-05-01 | 05 (tests) | 3 | STORE-02, STORE-03 | unit | `cd backend && python -m pytest tests/patient/ -v` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/patient/__init__.py` — package marker (empty file)
- [ ] `backend/tests/patient/test_patient_store.py` — stub test file with 7 test case stubs covering STORE-02 and STORE-03
- [ ] No framework install needed — pytest 8.2.0 already installed

*Wave 0 must be complete before plan wave 2 tasks execute.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| 5 patient tables + analyte_aliases created | STORE-01 | Requires live Supabase database connection | Apply `supabase/migrations/20260405000000_patient_tables.sql` via Supabase Dashboard or CLI; verify tables appear in Table Editor |
| analyte_aliases seeded with 20+ Brazilian terms | STORE-01 | Requires live DB | `SELECT count(*) FROM analyte_aliases` should return >= 20 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
