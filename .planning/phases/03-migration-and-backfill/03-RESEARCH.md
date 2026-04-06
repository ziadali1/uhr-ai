# Phase 3: Migration and Backfill - Research

**Researched:** 2026-04-06
**Domain:** Python batch migration scripts, Supabase PostgreSQL idempotent backfill, dry-run patterns
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| STORE-04 | System migrates existing manual `health_entries` records into new patient tables without data loss | health_entries schema fully read from health_store.py and models/health.py; mapping to patient_medications/allergies/conditions is 1:1 per HealthEntryType enum |
| STORE-05 | System backfills existing documents' `structured_result` JSONB into new patient tables | supabase_store.list_by_user() fetches all documents; _row_to_detail() already deserializes structured_result → StructuredResult; promote_to_patient_tables() already handles all 4 families |
</phase_requirements>

---

## Summary

Phase 3 has two distinct migration jobs, both of which can reuse Phase 2 infrastructure almost entirely.

**Job 1 — health_entries migration (`migrate_health_entries.py`):** The existing `health_entries` table stores manual patient entries typed by an enum: `medication_current`, `medication_past`, `complaint`, `allergy`. Each maps directly to one of the new patient tables. `medication_current` and `medication_past` → `patient_medications`, `allergy` → `patient_allergies`, `complaint` → `patient_conditions`. The source model (`HealthEntry` in `models/health.py`) provides `name`, `details`, `started_at`, `ended_at`, `active` fields. The migration is pure Python — read all rows from `health_entries` using the existing `health_store.list_by_user()` pattern, transform to patient table rows, upsert using the same `patient_store.py` patterns from Phase 2.

**Job 2 — documents backfill (`backfill_patient_tables.py`):** All existing documents already have `structured_result` JSONB in Supabase (written before Phase 2 promotion was wired into uploads). `supabase_store.list_by_user()` fetches and deserializes them. `promote_to_patient_tables()` is already idempotent and handles all 4 document families. The backfill script simply iterates all documents and calls `promote_to_patient_tables()` per document — this is nearly a one-liner reuse of Phase 2 work.

**Primary recommendation:** Scripts live in `backend/scripts/`. Both share a `--dry-run` flag and a common `--user-id` argument. Both use the existing Supabase client singleton from `supabase_store.py`. No new libraries required.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| supabase-py | 2.4.6 (installed) | Read health_entries; read documents; upsert patient tables | Already used in every store module; `.upsert(on_conflict=...)` pattern established in Phase 2 |
| pydantic | 2.7.1 (installed) | HealthEntry deserialization; StructuredResult deserialization | Project standard; all models already Pydantic 2.x |
| python-dotenv | installed (loaded in main.py) | Load SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY when running scripts standalone | Required for scripts that run outside FastAPI context |
| argparse (stdlib) | built-in | `--dry-run`, `--user-id`, `--verbose` flags | No extra dependency; sufficient for CLI scripts |
| pytest | 8.2.0 (installed) | Unit tests for migration logic | Project standard; 48-test suite established |

### No New Dependencies Required

All required libraries are already installed. No `pip install` step needed.

**Installation:** (none — all dependencies satisfied)

**Version verification:** Confirmed 2026-04-06 via:
- `python -c "import supabase; print(supabase.__version__)"` → 2.4.6
- `python -c "import pydantic; print(pydantic.__version__)"` → 2.7.1
- `python -m pytest --version` → pytest 8.2.0
- `python --version` → 3.11.9

---

## Architecture Patterns

### Recommended Project Structure

```
backend/
├── scripts/
│   ├── __init__.py                         # already exists
│   ├── migrate_health_entries.py           # NEW: STORE-04
│   └── backfill_patient_tables.py          # NEW: STORE-05
├── tests/
│   └── scripts/
│       ├── __init__.py                     # NEW: package marker
│       ├── test_migrate_health_entries.py  # NEW: unit tests for STORE-04
│       └── test_backfill_patient_tables.py # NEW: unit tests for STORE-05
```

### Pattern 1: Dry-Run Mode with Reporting

**What:** Every write is gated behind an `if not dry_run:` check. In dry-run mode, the script prints what it would create without touching the DB.

**When to use:** Both migration scripts. The dry-run flag must be explicit — default should be `dry_run=False` so a plain invocation actually runs.

**Example:**
```python
# backend/scripts/migrate_health_entries.py
import argparse

def main():
    parser = argparse.ArgumentParser(description="Migrate health_entries to patient tables")
    parser.add_argument("--user-id", required=True, help="Supabase user_id to migrate")
    parser.add_argument("--dry-run", action="store_true", help="Report without writing")
    parser.add_argument("--verbose", action="store_true", help="Print each row being processed")
    args = parser.parse_args()

    run_migration(user_id=args.user_id, dry_run=args.dry_run, verbose=args.verbose)
```

### Pattern 2: Idempotent Migration (Reuse Phase 2 Upserts)

**What:** Both scripts can safely be re-run any number of times. The idempotency comes from reusing Phase 2 upsert patterns:
- `patient_conditions`, `patient_medications`, `patient_allergies`: `on_conflict="user_id,normalized_X"` — second run is a no-op update
- `patient_observations`: pre-check SELECT + conditional insert (identical → skip, conflict → needs_review flag)

**Key insight:** `promote_to_patient_tables()` is already idempotent by design (D-06). The backfill script merely calls it per document — idempotency is inherited for free.

**Example:**
```python
# backend/scripts/backfill_patient_tables.py
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv()

from services.supabase_store import _get_client, list_by_user
from services.patient_store import promote_to_patient_tables

def run_backfill(user_id: str, dry_run: bool = False, verbose: bool = False) -> dict:
    """Iterate all documents for user_id and promote structured_result into patient tables.

    Returns summary: {total, skipped_no_sr, promoted, errors}
    """
    docs = list_by_user(user_id)
    total = len(docs)
    skipped = 0
    promoted = 0
    errors = 0

    for doc in docs:
        if doc.structured_result is None:
            skipped += 1
            if verbose:
                print(f"  SKIP {doc.document_id} — no structured_result")
            continue
        if dry_run:
            family = doc.structured_result.document_family
            print(f"  DRY-RUN would promote {doc.document_id} ({family})")
            promoted += 1
            continue
        try:
            promote_to_patient_tables(
                doc_id=doc.document_id,
                user_id=user_id,
                structured_result=doc.structured_result,
                upload_date=doc.upload_date.strftime("%Y-%m-%d"),
            )
            promoted += 1
            if verbose:
                print(f"  OK {doc.document_id}")
        except Exception as exc:
            errors += 1
            print(f"  ERROR {doc.document_id}: {exc}")

    return {"total": total, "skipped": skipped, "promoted": promoted, "errors": errors}
```

### Pattern 3: health_entries Type Mapping

**What:** `HealthEntryType` enum maps to patient tables as follows:

| HealthEntryType | Target Table | Mapping Notes |
|-----------------|-------------|---------------|
| `medication_current` | `patient_medications` | `name` → raw/normalized, `details` → `dose` (best-effort), `status='active'` |
| `medication_past` | `patient_medications` | same as above, `status='stopped'` |
| `complaint` | `patient_conditions` | `name` → raw/normalized, `details` absorbed into `raw_condition`, `clinical_status='active'`, `verification_status=None` (manually entered, not LLM-confirmed) |
| `allergy` | `patient_allergies` | `name` → raw/normalized_allergen, `details` → `reaction` |

**Dedup:** Uses the same `on_conflict` upsert pattern as `patient_store.py`. `normalized_X = name.strip().lower()`.

**Source document_id:** health_entries have no `document_id`; use `None` for the `document_id` column. This is allowed — the column is nullable in the migration SQL.

**Example:**
```python
# Source: backend/services/health_store.py + models/health.py
from models.health import HealthEntry, HealthEntryType

def _map_to_medication(entry: HealthEntry, user_id: str) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "document_id": None,                     # no document source for manual entries
        "raw_medication": entry.name,
        "normalized_medication": entry.name.strip().lower(),
        "dose": entry.details,                   # best-effort: details sometimes contains dose
        "route": None,
        "frequency": None,
        "status": "active" if entry.entry_type == HealthEntryType.medication_current else "stopped",
    }

def _map_to_condition(entry: HealthEntry, user_id: str) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "document_id": None,
        "raw_condition": entry.name,
        "normalized_condition": entry.name.strip().lower(),
        "clinical_status": "active",
        "verification_status": None,             # manually entered — not LLM-confirmed
    }

def _map_to_allergy(entry: HealthEntry, user_id: str) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "document_id": None,
        "raw_allergen": entry.name,
        "normalized_allergen": entry.name.strip().lower(),
        "reaction": entry.details,
    }
```

### Pattern 4: Completeness Verification Queries

**What:** After migration, run count queries to confirm all source records have a corresponding destination row. These can be standalone functions or printed at the end of the migration run.

**Example:**
```python
def verify_completeness(client, user_id: str) -> None:
    """Print pre/post counts for STORE-04 and STORE-05 completeness check."""
    # STORE-04: health_entries vs patient tables
    he = client.table("health_entries").select("id", count="exact").eq("user_id", user_id).execute()
    meds = client.table("patient_medications").select("id", count="exact").eq("user_id", user_id).execute()
    allergies = client.table("patient_allergies").select("id", count="exact").eq("user_id", user_id).execute()
    conditions = client.table("patient_conditions").select("id", count="exact").eq("user_id", user_id).execute()
    print(f"health_entries total: {he.count}")
    print(f"patient_medications rows: {meds.count}")
    print(f"patient_allergies rows: {allergies.count}")
    print(f"patient_conditions rows: {conditions.count}")

    # STORE-05: documents with structured_result vs promoted
    docs = client.table("documents").select("id", count="exact").eq("user_id", user_id).not_.is_("structured_result", "null").execute()
    obs = client.table("patient_observations").select("id", count="exact").eq("user_id", user_id).execute()
    print(f"documents with structured_result: {docs.count}")
    print(f"patient_observations rows: {obs.count}")
```

### Anti-Patterns to Avoid

- **Calling `health_store.list_by_user()` directly from the script:** This function applies `.eq("active", True)` and `.order("created_at")` — it only returns active entries. For migration, ALL entries (including inactive) should be fetched directly via the Supabase client to ensure zero data loss.
- **Deleting `health_entries` after migration:** The "done when" criteria explicitly keeps the old table as backup. Never drop it in Phase 3.
- **Running the backfill without `--user-id`:** Without scoping to a user, the query fetches all users' documents. Phase 3 targets a single-user system so this should be fine, but providing `--user-id` explicitly maintains consistency and allows future multi-user use.
- **Importing from `api/` modules inside scripts:** API modules import FastAPI which requires a running event loop. Scripts must import from `services/` and `models/` only.
- **Calling `promote_to_patient_tables()` without loading `.env`:** The `_get_client()` singleton reads `SUPABASE_URL` from environment. Scripts running outside FastAPI won't have env vars set — must call `load_dotenv()` at top of script before any service import.
- **Counting destination rows as a 1:1 check for health_entries:** health_entries with duplicate names will collapse to one row in patient tables (upsert on normalized name). Count checks must account for this — destination count <= source count is expected when duplicates exist.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Idempotent patient table inserts | Custom INSERT ... ON CONFLICT ... DO UPDATE | `client.table(...).upsert(row, on_conflict="cols").execute()` | Already established in patient_store.py; tested; handles constraint correctly |
| Document list with structured_result | Raw SQL SELECT | `supabase_store.list_by_user(user_id)` | Already implemented; deserializes structured_result JSONB into StructuredResult Pydantic model |
| Structured result promotion | Re-implementing promotion logic | `promote_to_patient_tables()` from patient_store.py | Already implements all 4 families + dedup + alias lookup + date parsing; reuse is the entire design |
| Loading env vars in scripts | os.environ reads with no fallback | `from dotenv import load_dotenv; load_dotenv()` | Scripts run outside FastAPI; dotenv is already imported in main.py and is in the project |
| Checking Supabase count | ORM query | `client.table(...).select("id", count="exact").execute()` then `.count` | Supabase SDK supports PostgREST `?select=id&head=true` count via this pattern |

**Key insight:** STORE-05 (backfill) is almost entirely reuse. The backfill script is a thin for-loop over `list_by_user()` + `promote_to_patient_tables()`. The only new logic is the dry-run flag and completeness reporting.

---

## Runtime State Inventory

Both jobs are migration/backfill operations — this section is required.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | `health_entries` table in Supabase: existing manual patient records (medications, allergies, complaints) | Data migration — read all rows (not just active), map to patient tables, upsert |
| Stored data | `documents` table in Supabase: existing documents with `structured_result` JSONB non-null | Data migration — iterate, call promote_to_patient_tables per document |
| Live service config | None — no external service config embeds these table names | None |
| OS-registered state | None — no OS-level tasks reference health_entries | None |
| Secrets/env vars | `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` — required by scripts at runtime; not renamed | Ensure `.env` is loaded before running scripts |
| Build artifacts | None | None |

**Key finding for STORE-04:** `health_store.list_by_user()` has `.eq("active", True)` filter — this silently drops inactive/deleted entries. The migration script MUST query `health_entries` directly (no active filter) to guarantee zero data loss. This is the critical difference between using the existing service function vs. the raw client.

**Nothing found in remaining categories:** Verified by reading health_store.py, supabase_store.py, and all service files — no OS registrations, no external service configs, no build artifacts reference the table names being migrated.

---

## Common Pitfalls

### Pitfall 1: `health_store.list_by_user()` Silently Drops Inactive Entries

**What goes wrong:** Using the existing `list_by_user()` function in the migration script causes silent data loss. The function hard-codes `.eq("active", True)` — any entry that was marked inactive (soft-deleted) never gets migrated.

**Why it happens:** The health_store was built for the frontend (show active entries only). Migration requires ALL entries regardless of active status.

**How to avoid:** Query `health_entries` directly:
```python
client.table("health_entries").select("*").eq("user_id", user_id).execute()
```
Do NOT call `health_store.list_by_user()` in the migration script.

**Warning signs:** health_entries count in DB exceeds the count in patient tables after migration.

### Pitfall 2: Missing `load_dotenv()` in Scripts

**What goes wrong:** Running `python scripts/migrate_health_entries.py` raises `KeyError: 'SUPABASE_URL'` — environment variables aren't set outside the FastAPI server context.

**Why it happens:** `_get_client()` reads `os.environ["SUPABASE_URL"]` directly with no default. When running a standalone script, the FastAPI startup that normally loads `.env` via `python-dotenv` (main.py) does not run.

**How to avoid:** First lines of both scripts:
```python
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from dotenv import load_dotenv
load_dotenv()  # MUST be before any service import
```

**Warning signs:** `KeyError: 'SUPABASE_URL'` or `KeyError: 'SUPABASE_SERVICE_ROLE_KEY'` at script startup.

### Pitfall 3: `document_id=None` Constraint

**What goes wrong:** The migration maps health_entries with no source document. If `patient_medications.document_id` has a NOT NULL constraint or a FK to `documents`, the insert fails.

**Why it happens:** health_entries are manual entries with no corresponding document row.

**How to avoid:** Verified from migration SQL (`supabase/migrations/20260405000000_patient_tables.sql`): `document_id TEXT` with no NOT NULL and no FK constraint. `None` → PostgreSQL NULL is safe.

**Warning signs:** FK violation or NOT NULL constraint error on document_id column.

### Pitfall 4: Upsert Count vs Source Count Discrepancy

**What goes wrong:** After migration, `SELECT count(*) FROM patient_medications` returns fewer rows than `SELECT count(*) FROM health_entries WHERE entry_type IN ('medication_current', 'medication_past')`. This looks like data loss but is actually correct dedup behavior.

**Why it happens:** If a user has "Metformina" in both `medication_current` and `medication_past`, the upsert on `normalized_medication` collapses them to one row (latest-wins per D-02). This is the intended behavior.

**How to avoid:** Document this expectation clearly in the verification step. The completeness check should compare source unique-name count vs destination count, not raw row count.

**Warning signs:** Team flags "data loss" based on count mismatch; investigation shows the "lost" entries had duplicate normalized names.

### Pitfall 5: Backfill Re-Run Creates `needs_review` Observations Spuriously

**What goes wrong:** Running `backfill_patient_tables.py` twice creates `needs_review=True` rows for every lab observation, because the pre-check SELECT finds the row inserted in run 1, and the second run sees `value_str` match but something else differs.

**Why it happens:** This would only happen if `promote_to_patient_tables()` has a bug in the identical-value detection. Based on Phase 2 code review, the pre-check compares `value_str` and `unit` exactly — if they match, the function returns early without inserting. The idempotency is correct.

**How to avoid:** Verify with the existing test `test_duplicate_observation_identical_is_noop` (already passes). The backfill inherits this behavior. No additional action required.

**Warning signs:** Growing `patient_observations` count across multiple script runs; `needs_review=True` rows for values that were never actually ambiguous.

### Pitfall 6: `structured_result` is NULL for Older Documents

**What goes wrong:** Documents uploaded before Phase 2 structured extraction was wired may have `structured_result = NULL`. The backfill script calls `promote_to_patient_tables()` which already handles `None` (returns immediately). This is fine.

**Why it happens:** `structured_result` was added to the pipeline in Phase 2 — documents predating that wiring have no structured data. `promote_to_patient_tables()` already has `if structured_result is None: return`.

**How to avoid:** No code change needed. The dry-run output should clearly report skipped documents with null structured_result so the user can distinguish "skipped by design" from actual failures.

**Warning signs:** User panics seeing "X documents skipped" output — this is expected and should be labeled "SKIP (no structured_result)" in the script output.

---

## Code Examples

### Verified health_entries Schema (from health_store.py and models/health.py)

```python
# Source: backend/models/health.py (read 2026-04-06)
class HealthEntryType(str, Enum):
    medication_current = "medication_current"
    medication_past    = "medication_past"
    complaint          = "complaint"
    allergy            = "allergy"

class HealthEntry(HealthEntryCreate):
    id: str
    user_id: str
    active: bool
    created_at: datetime
    # plus from HealthEntryCreate:
    # entry_type, name, details (str|None), started_at (date|None), ended_at (date|None)
```

### Verified documents Query Pattern (from supabase_store.py)

```python
# Source: backend/services/supabase_store.py (read 2026-04-06)
# list_by_user already does deserialization including structured_result → StructuredResult
def list_by_user(user_id: str) -> list[DocumentDetail]:
    client = _get_client()
    res = (
        client.table("documents")
        .select("*")
        .eq("user_id", user_id)
        .order("upload_date", desc=True)
        .execute()
    )
    return [_row_to_detail(row) for row in (res.data or [])]
```

The backfill script should call this directly — deserialization of `structured_result` JSONB is already handled.

### promote_to_patient_tables Signature (from patient_store.py)

```python
# Source: backend/services/patient_store.py (read 2026-04-06)
def promote_to_patient_tables(
    doc_id: str,
    user_id: str,
    structured_result: StructuredResult | None,
    upload_date: str | None = None,  # ISO YYYY-MM-DD, used as fallback when collection_date is None
) -> None:
    """Soft-fail: never raises. Handles structured_lab, clinical_narrative, medication_document, imaging_narrative."""
```

The `upload_date` argument should be `doc.upload_date.strftime("%Y-%m-%d")` when calling from backfill — this matches the pattern in upload.py line 125.

### Unit Test Pattern for Migration Scripts

```python
# backend/tests/scripts/test_migrate_health_entries.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from unittest.mock import MagicMock, patch
from models.health import HealthEntry, HealthEntryType
from datetime import datetime, timezone


def _make_entry(entry_type, name, details=None, active=True):
    return HealthEntry(
        id="entry-1",
        user_id="user-1",
        entry_type=entry_type,
        name=name,
        details=details,
        active=active,
        created_at=datetime.now(timezone.utc),
    )


def test_inactive_entry_is_migrated():
    """CRITICAL: inactive entries (active=False) must still be migrated — zero data loss."""
    entry = _make_entry(HealthEntryType.medication_past, "Amoxicilina", active=False)
    # verify the migration includes it regardless of active flag
    ...


def test_medication_current_maps_to_active_status():
    ...


def test_complaint_maps_to_patient_conditions():
    ...


def test_allergy_maps_to_patient_allergies_with_reaction():
    ...


def test_dry_run_does_not_call_upsert():
    ...
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| health_entries: no migration needed (no patient tables existed) | Migrate to patient_medications, patient_allergies, patient_conditions | Phase 3 | health_entries can be archived; patient tables become authoritative |
| documents.structured_result queried per-document via JSONB | Promoted into indexed patient rows via backfill | Phase 3 | SQL aggregation, timeline queries, and Phase 5 routing become viable |
| Python migration scripts commonly use Alembic for schema | This project uses Supabase migrations (raw SQL via Dashboard/CLI) | Established in Phase 2 | Scripts use Supabase Python SDK directly, not Alembic |

**No deprecated approaches in this phase.** Both scripts are greenfield additions.

---

## Open Questions

1. **user_id for migration — single user or all users?**
   - What we know: STATE.md confirms this is a single-patient system. health_entries and documents all belong to one user_id.
   - What's unclear: The actual user_id string value in the live database isn't known from source code alone.
   - Recommendation: Scripts accept `--user-id` as a required argument (explicit is better than auto-detect). The verification step should print the user_id to confirm.

2. **health_entries: should started_at/ended_at map to patient_medications?**
   - What we know: `patient_medications` has no `started_at`/`ended_at` columns per the Phase 2 migration SQL. `health_entries` has these date fields.
   - What's unclear: Whether the Phase 3 plan should add `started_at`/`ended_at` to `patient_medications` or silently drop them.
   - Recommendation: Drop them silently for Phase 3. The Phase 2 schema doesn't include date range columns for medications. Adding schema changes would be out of scope for this phase and require a new migration. The planner should flag this as a known data-loss tradeoff and document it explicitly.

3. **documents without structured_result — how many exist?**
   - What we know: Documents uploaded before Phase 2 structured extraction wiring have `structured_result = NULL`. `promote_to_patient_tables(None)` is a no-op.
   - What's unclear: The exact proportion of documents with null vs non-null structured_result in the live DB — this can only be known from a live DB query.
   - Recommendation: The verification step should print count of documents with null structured_result so the user can evaluate whether re-processing older documents (outside Phase 3 scope) is needed.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11 | Migration scripts | Yes | 3.11.9 | — |
| supabase-py | Supabase reads/writes | Yes | 2.4.6 | — |
| pydantic | Model deserialization | Yes | 2.7.1 | — |
| python-dotenv | Env loading in scripts | Assumed yes (used in main.py) | — | Manual export of env vars |
| pytest | Unit tests | Yes | 8.2.0 | — |
| Supabase live DB | End-to-end migration | Remote (Supabase cloud) | — | Cannot test live migration locally without credentials |
| health_entries table | STORE-04 | Exists in schema (verified from health_store.py + models) | — | — |
| patient_* tables | Both jobs | Depends on Phase 2 migration SQL being applied | — | Must apply migration before running backfill |

**Missing dependencies with no fallback:**
- Phase 2 migration (`supabase/migrations/20260405000000_patient_tables.sql`) must have been applied to the live Supabase instance. If patient tables don't exist, both scripts will fail with a table-not-found error. The plan must include a pre-flight check (or rely on the human verification note in Phase 2).

**Missing dependencies with fallback:**
- python-dotenv: if not installed, user can manually export SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY before running scripts. Likely installed since it appears in main.py.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.2.0 |
| Config file | none (pytest.ini not present; tests discovered by default) |
| Quick run command | `cd backend && python -m pytest tests/scripts/ -v` |
| Full suite command | `cd backend && python -m pytest tests/ -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| STORE-04 | medication_current entry maps to patient_medications with status='active' | unit | `cd backend && python -m pytest tests/scripts/test_migrate_health_entries.py -x` | Wave 0 |
| STORE-04 | medication_past entry maps to patient_medications with status='stopped' | unit | same | Wave 0 |
| STORE-04 | complaint entry maps to patient_conditions with clinical_status='active' | unit | same | Wave 0 |
| STORE-04 | allergy entry maps to patient_allergies with details as reaction | unit | same | Wave 0 |
| STORE-04 | inactive entry (active=False) is still migrated (zero data loss) | unit | same | Wave 0 |
| STORE-04 | dry-run mode does not call upsert | unit | same | Wave 0 |
| STORE-05 | documents with structured_result are promoted via promote_to_patient_tables | unit | `cd backend && python -m pytest tests/scripts/test_backfill_patient_tables.py -x` | Wave 0 |
| STORE-05 | documents with structured_result=None are skipped (not an error) | unit | same | Wave 0 |
| STORE-05 | backfill is idempotent (second run same result as first) | unit (inherits from Phase 2 patient_store tests) | `cd backend && python -m pytest tests/patient/ tests/scripts/ -x` | Phase 2 Wave 0 done + Wave 0 |
| STORE-05 | dry-run mode reports what would be created without writing | unit | same | Wave 0 |
| Both | verify_completeness() prints correct before/after counts | manual (requires live DB) | N/A | — |

### Sampling Rate

- **Per task commit:** `cd backend && python -m pytest tests/scripts/ -x`
- **Per wave merge:** `cd backend && python -m pytest tests/ -v`
- **Phase gate:** Full 48+ test suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `backend/tests/scripts/__init__.py` — package marker
- [ ] `backend/tests/scripts/test_migrate_health_entries.py` — covers STORE-04 (6 test cases above)
- [ ] `backend/tests/scripts/test_backfill_patient_tables.py` — covers STORE-05 (4 test cases above)
- [ ] No framework install needed — pytest already installed

*(Existing 48 tests continue to pass — no regression expected since scripts are additive)*

---

## Sources

### Primary (HIGH confidence)

- `backend/services/health_store.py` — direct read; health_entries query patterns, active filter confirmed
- `backend/models/health.py` — direct read; HealthEntryType enum, HealthEntry fields confirmed
- `backend/services/supabase_store.py` — direct read; list_by_user(), _row_to_detail(), structured_result deserialization confirmed
- `backend/services/patient_store.py` — direct read; promote_to_patient_tables() signature, idempotency design, all 4 family handlers confirmed
- `supabase/migrations/20260405000000_patient_tables.sql` — direct read; document_id TEXT (nullable, no FK), UNIQUE constraints confirmed
- `backend/api/upload.py` — direct read; upload_date.strftime("%Y-%m-%d") pattern for promote call confirmed
- `backend/tests/patient/test_patient_store.py` — direct read; test patterns for Phase 3 tests to follow
- `.planning/phases/02-longitudinal-patient-data-model/02-VERIFICATION.md` — confirmed 48 tests pass; patient tables schema verified

### Secondary (MEDIUM confidence)

- `backend/main.py` — confirms python-dotenv is in project (referenced for script env loading)
- Supabase Python SDK docs (verified in Phase 2 research) — `.upsert(on_conflict=...)` and count query patterns

### Tertiary (LOW confidence)

- None — all critical claims verified from source code.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries verified installed and in active use; no new dependencies
- Architecture: HIGH — health_entries schema read directly; patient table SQL read directly; promote_to_patient_tables() signature verified; upsert patterns proven in Phase 2
- Pitfalls: HIGH — active-filter trap verified from health_store.py line 44; dotenv trap verified from _get_client() direct env read; count-mismatch trap verified from D-02 dedup semantics
- Test patterns: HIGH — Phase 2 test files read directly; 48 passing tests confirmed

**Research date:** 2026-04-06
**Valid until:** 2026-05-06 (stable stack; no external service changes anticipated)
