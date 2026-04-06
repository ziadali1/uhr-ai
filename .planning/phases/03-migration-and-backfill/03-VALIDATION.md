---
phase: 3
slug: migration-and-backfill
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-06
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pytest.ini` or `pyproject.toml` |
| **Quick run command** | `pytest tests/ -x -q` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ -x -q`
- **After every plan wave:** Run `pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 3-01-01 | 01 | 1 | STORE-04 | integration | `python scripts/migrate_health_entries.py --dry-run --user-id test` | ✅ | ⬜ pending |
| 3-01-02 | 01 | 1 | STORE-04 | integration | `python scripts/migrate_health_entries.py --dry-run --user-id test` | ✅ | ⬜ pending |
| 3-02-01 | 02 | 1 | STORE-05 | integration | `python scripts/backfill_patient_tables.py --dry-run --user-id test` | ✅ | ⬜ pending |
| 3-02-02 | 02 | 1 | STORE-05 | integration | `python scripts/backfill_patient_tables.py --dry-run --user-id test` | ✅ | ⬜ pending |
| 3-03-01 | 03 | 2 | STORE-04, STORE-05 | manual | Count query before/after in Supabase | ❌ manual | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `scripts/migrate_health_entries.py` — dry-run mode for STORE-04 migration
- [ ] `scripts/backfill_patient_tables.py` — dry-run mode for STORE-05 backfill

*If none: "Existing infrastructure covers all phase requirements."*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Zero data loss after migration | STORE-04 | Requires live DB with actual data | Run `SELECT COUNT(*) FROM health_entries` before; run migrate script; compare counts in patient tables |
| All documents backfilled | STORE-05 | Requires live DB with structured_result rows | Run `SELECT COUNT(*) FROM documents WHERE structured_result IS NOT NULL` before; run backfill; verify patient table counts match |
| Idempotent re-run (no duplicates) | STORE-04, STORE-05 | Requires live DB state | Run scripts twice; verify no duplicate rows created |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
