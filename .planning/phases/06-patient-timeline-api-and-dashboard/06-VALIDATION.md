---
phase: 6
slug: patient-timeline-api-and-dashboard
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-08
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (backend) / Vitest (frontend) |
| **Config file** | `pytest.ini` or `pyproject.toml` / `vitest.config.ts` |
| **Quick run command** | `pytest tests/ -x -q` |
| **Full suite command** | `pytest tests/ -q && npm run test --prefix app` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ -x -q`
- **After every plan wave:** Run `pytest tests/ -q && npm run test --prefix app`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 6-01-01 | 01 | 1 | TIMELINE-01 | integration | `pytest tests/test_timeline_api.py -x -q` | ❌ W0 | ⬜ pending |
| 6-01-02 | 01 | 1 | TIMELINE-01 | integration | `pytest tests/test_timeline_api.py -x -q` | ❌ W0 | ⬜ pending |
| 6-02-01 | 02 | 1 | TIMELINE-02 | integration | `pytest tests/test_patient_summary.py -x -q` | ❌ W0 | ⬜ pending |
| 6-03-01 | 03 | 2 | TIMELINE-02 | integration | `pytest tests/test_emergency.py -x -q` | ❌ W0 | ⬜ pending |
| 6-04-01 | 04 | 3 | TIMELINE-03 | e2e/manual | See Manual-Only | N/A | ⬜ pending |
| 6-05-01 | 05 | 3 | TIMELINE-03 | e2e/manual | See Manual-Only | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_timeline_api.py` — stubs for TIMELINE-01 (observations, conditions, medications endpoints)
- [ ] `tests/test_patient_summary.py` — stubs for TIMELINE-02 (patient summary endpoint)
- [ ] `tests/test_emergency.py` — stubs for emergency.py refactor (TIMELINE-02)
- [ ] `tests/conftest.py` — shared fixtures (mock supabase client, sample patient data)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Dashboard shows active conditions, medications, latest labs | TIMELINE-03 | Requires browser render with live Supabase data | Open dashboard at `/dashboard`, verify PatientSummary panel shows data without console errors |
| Emergency profile page uses patient tables not document scan | TIMELINE-03 | Requires E2E browser check | Navigate to emergency profile, confirm data loads without calling `list_by_user()` document endpoint |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
