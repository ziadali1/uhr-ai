"""
Patient Query Service — read-path queries for patient timeline and summary endpoints.

Implements Phase 6 data access layer:
  - get_observations_timeline(): sorted lab observations per analyte with enrichment
  - get_patient_summary(): aggregated summary with active conditions, medications, allergies, latest labs
  - get_conditions() / get_medications(): simple per-user table reads
  - All public functions soft-fail: log warning and return None or [] on any exception
"""
import logging

from services.supabase_store import _get_client

_log = logging.getLogger(__name__)


# ── Public functions ──────────────────────────────────────────────────────────

def get_observations_timeline(
    user_id: str,
    analyte: str,
    date_from: str | None = None,
    date_to: str | None = None,
) -> list[dict]:
    """Return observations for a specific analyte, sorted by observed_date descending.

    Applies optional date range filters. Each row is enriched with derived fields
    (value_num, ref_low, ref_high) via _enrich_observation().

    Soft-fail: returns [] on any exception.
    """
    try:
        client = _get_client()
        query = (
            client.table("patient_observations")
            .select("*")
            .eq("user_id", user_id)
            .eq("normalized_analyte", analyte)
            .order("observed_date", desc=True)
        )
        if date_from:
            query = query.gte("observed_date", date_from[:10])
        if date_to:
            query = query.lte("observed_date", date_to[:10])
        res = query.execute()
        return [_enrich_observation(row) for row in (res.data or [])]
    except Exception as exc:
        _log.warning("get_observations_timeline failed user_id=%s analyte=%s: %s", user_id, analyte, exc)
        return []


def get_patient_summary(user_id: str) -> dict | None:
    """Return aggregated patient summary: active conditions, current medications, allergies, latest labs.

    Soft-fail: returns None on any exception.
    """
    try:
        client = _get_client()
        conditions = _query_active_conditions(client, user_id)
        medications = _query_current_medications(client, user_id)
        allergies = _query_allergies(client, user_id)
        latest_labs = _query_latest_labs(client, user_id)
        return {
            "user_id": user_id,
            "active_conditions": conditions,
            "current_medications": medications,
            "allergies": allergies,
            "latest_labs": latest_labs,
        }
    except Exception as exc:
        _log.warning("get_patient_summary failed user_id=%s: %s", user_id, exc)
        return None


def get_conditions(user_id: str) -> list[dict]:
    """Return all conditions for a user from patient_conditions.

    Soft-fail: returns [] on any exception.
    """
    try:
        client = _get_client()
        res = client.table("patient_conditions").select("*").eq("user_id", user_id).execute()
        return res.data or []
    except Exception as exc:
        _log.warning("get_conditions failed user_id=%s: %s", user_id, exc)
        return []


def get_medications(user_id: str) -> list[dict]:
    """Return all medications for a user from patient_medications.

    Soft-fail: returns [] on any exception.
    """
    try:
        client = _get_client()
        res = client.table("patient_medications").select("*").eq("user_id", user_id).execute()
        return res.data or []
    except Exception as exc:
        _log.warning("get_medications failed user_id=%s: %s", user_id, exc)
        return []


# ── Private helpers ───────────────────────────────────────────────────────────

def _query_active_conditions(client, user_id: str) -> list[dict]:
    """Query patient_conditions filtered to active clinical_status."""
    res = (
        client.table("patient_conditions")
        .select("*")
        .eq("user_id", user_id)
        .eq("clinical_status", "active")
        .execute()
    )
    return res.data or []


def _query_current_medications(client, user_id: str) -> list[dict]:
    """Query patient_medications filtered to active status."""
    res = (
        client.table("patient_medications")
        .select("*")
        .eq("user_id", user_id)
        .eq("status", "active")
        .execute()
    )
    return res.data or []


def _query_allergies(client, user_id: str) -> list[dict]:
    """Query all patient_allergies for a user."""
    res = (
        client.table("patient_allergies")
        .select("*")
        .eq("user_id", user_id)
        .execute()
    )
    return res.data or []


def _query_latest_labs(client, user_id: str) -> list[dict]:
    """Return the most recent observation per normalized_analyte.

    Queries observations ordered by observed_date desc, then deduplicates
    by normalized_analyte keeping the first (most recent) per analyte.
    Each kept row is enriched via _enrich_observation().
    """
    res = (
        client.table("patient_observations")
        .select(
            "normalized_analyte,raw_analyte,value_str,unit,reference_range,"
            "flag,needs_review,observed_date,document_id"
        )
        .eq("user_id", user_id)
        .order("observed_date", desc=True)
        .execute()
    )
    seen: set[str] = set()
    result: list[dict] = []
    for row in (res.data or []):
        analyte = row.get("normalized_analyte", "")
        if analyte in seen:
            continue
        seen.add(analyte)
        result.append(_enrich_observation(row))
    return result


def _enrich_observation(row: dict) -> dict:
    """Derive computed fields from a raw patient_observations row.

    Computes:
      - value_num: float cast of value_str, None on failure
      - ref_low / ref_high: parsed from reference_range "low-high" string, None on failure
      - Renamed fields: observed_at, analyte_raw, analyte_norm for API response shape
    """
    observed_at = row.get("observed_date")
    analyte_raw = row.get("raw_analyte")
    analyte_norm = row.get("normalized_analyte")

    # Parse value_num
    try:
        value_num: float | None = float(row.get("value_str", ""))
    except (ValueError, TypeError):
        value_num = None

    # Parse ref_low / ref_high from reference_range string (format: "3.5-5.0")
    ref_low: float | None = None
    ref_high: float | None = None
    ref_range = row.get("reference_range")
    if ref_range and isinstance(ref_range, str) and "-" in ref_range:
        parts = ref_range.split("-", 1)
        try:
            ref_low = float(parts[0])
            ref_high = float(parts[1])
        except (ValueError, TypeError):
            ref_low = None
            ref_high = None

    return {
        "observed_at": observed_at,
        "value_num": value_num,
        "value_str": row.get("value_str"),
        "unit": row.get("unit"),
        "ref_low": ref_low,
        "ref_high": ref_high,
        "flag": row.get("flag"),
        "document_id": row.get("document_id"),
        "analyte_raw": analyte_raw,
        "analyte_norm": analyte_norm,
        "needs_review": row.get("needs_review"),
    }
