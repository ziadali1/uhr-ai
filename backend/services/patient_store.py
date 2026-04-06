"""
Patient Store — promotion of structured extraction results into patient tables.

Implements D-01 through D-07 per .planning/phases/02-longitudinal-patient-data-model/02-RESEARCH.md:
  - D-01: Observations dedup with conflict detection (needs_review flag)
  - D-02: Conditions/medications/allergies upsert, latest-document-wins
  - D-04: Soft-fail — promotion failure MUST NOT block document upload
  - D-05: On failure: log doc_id + error, do not raise
  - D-06: Promotion is idempotent (ON CONFLICT DO UPDATE)
  - D-07: Follow Phase 1 supabase_store.py soft-fail pattern
  - D-14/D-17: Alias lookup from analyte_aliases table, case-insensitive, fallback to lowercased name
"""

import logging
import uuid
from datetime import datetime

from models.document import (
    StructuredResult,
    StructuredLab,
    ClinicalNote,
    MedicationDocument,
    ImagingReport,
    LabFinding,
    MedicationEntry,
)
from services.supabase_store import _get_client

_log = logging.getLogger(__name__)


# ── Public entry point ────────────────────────────────────────────────────────

def promote_to_patient_tables(
    doc_id: str,
    user_id: str,
    structured_result: StructuredResult | None,
    upload_date: str | None = None,
) -> None:
    """Promote structured_result into patient tables. Soft-fail: never raises.

    Per D-04/D-05/D-07: any exception is caught, logged, and swallowed.
    Caller (upload.py) must NOT depend on this succeeding.
    """
    if structured_result is None:
        return

    try:
        client = _get_client()
        family = structured_result.document_family
        data = structured_result.structured_data

        if family == "structured_lab":
            _promote_lab(client, doc_id, user_id, StructuredLab(**data), upload_date)
        elif family == "clinical_narrative":
            _promote_clinical(client, doc_id, user_id, ClinicalNote(**data))
        elif family == "medication_document":
            _promote_medications(client, doc_id, user_id, MedicationDocument(**data))
        elif family == "imaging_narrative":
            _promote_imaging(client, doc_id, user_id, ImagingReport(**data))
        # Unknown families: skip silently (no error, no log)

    except Exception as exc:
        _log.warning("patient_store promotion failed doc_id=%s: %s", doc_id, exc)


# ── Alias lookup ──────────────────────────────────────────────────────────────

def _load_aliases(client) -> dict[str, str]:
    """Load analyte_aliases table as {raw_name_lower: canonical_name}.

    Per D-14: aliases are stored in Supabase analyte_aliases table.
    Returns empty dict on failure (table may not exist yet in dev).
    """
    try:
        res = client.table("analyte_aliases").select("raw_name,canonical_name").execute()
        return {row["raw_name"].lower(): row["canonical_name"] for row in (res.data or [])}
    except Exception:
        return {}


# ── Normalization ─────────────────────────────────────────────────────────────

def _normalize_analyte(raw: str, aliases: dict[str, str]) -> str:
    """Resolve raw analyte name to canonical form via alias lookup.

    Per D-17: case-insensitive. Falls back to lowercased raw name if no alias found.
    """
    return aliases.get(raw.strip().lower(), raw.strip().lower())


# ── Date parsing ──────────────────────────────────────────────────────────────

def _parse_br_date(date_str: str | None, fallback: str | None = None) -> str | None:
    """Parse Brazilian DD/MM/YYYY or ISO YYYY-MM-DD date strings to ISO format.

    Per Pitfall 1 in research: Brazilian lab reports use DD/MM/YYYY format.
    Per Pitfall 2: returns fallback (e.g. upload_date) when date_str is None to
    ensure a concrete date for the dedup key.
    """
    if date_str is None:
        return fallback
    try:
        return datetime.strptime(date_str, "%d/%m/%Y").strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        pass
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        pass
    return fallback


# ── Observation upsert (with conflict detection) ──────────────────────────────

def _promote_observation(
    client,
    user_id: str,
    doc_id: str,
    normalized_analyte: str,
    raw_analyte: str,
    finding: LabFinding,
    observed_date: str | None,
) -> None:
    """Insert one lab finding row into patient_observations.

    Per D-01: pre-check for existing row on (user_id, normalized_analyte, observed_date).
    - Identical value/unit → no-op (return early)
    - Different value/unit → insert NEW row with needs_review=True (conflict flagged)
    - No existing row → plain insert with needs_review=False
    """
    existing = (
        client.table("patient_observations")
        .select("id,value_str,unit")
        .eq("user_id", user_id)
        .eq("normalized_analyte", normalized_analyte)
        .eq("observed_date", observed_date)
        .execute()
    )

    needs_review = False
    if existing.data:
        ex = existing.data[0]
        if ex["value_str"] == finding.value and ex["unit"] == finding.unit:
            return  # identical — no-op (D-01)
        else:
            needs_review = True  # conflict — flag the newer row (D-01)

    row = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "document_id": doc_id,
        "normalized_analyte": normalized_analyte,
        "raw_analyte": raw_analyte,
        "value_str": finding.value,
        "unit": finding.unit,
        "reference_range": finding.reference_range,
        "flag": finding.flag,
        "observed_date": observed_date,
        "needs_review": needs_review,
    }
    client.table("patient_observations").insert(row).execute()


# ── Lab promotion ─────────────────────────────────────────────────────────────

def _promote_lab(
    client,
    doc_id: str,
    user_id: str,
    lab: StructuredLab,
    upload_date: str | None,
) -> None:
    """Promote a StructuredLab into patient_observations rows.

    Loads aliases once per document (not per finding) to avoid N+1 queries.
    Falls back to upload_date when collection_date is absent (Pitfall 2).
    """
    aliases = _load_aliases(client)
    observed = _parse_br_date(lab.collection_date, fallback=upload_date)

    for finding in lab.findings:
        normalized = _normalize_analyte(finding.name, aliases)
        _promote_observation(client, user_id, doc_id, normalized, finding.name, finding, observed)


# ── Clinical promotion ────────────────────────────────────────────────────────

def _promote_clinical(
    client,
    doc_id: str,
    user_id: str,
    note: ClinicalNote,
) -> None:
    """Promote a ClinicalNote into patient_conditions, patient_allergies, patient_medications.

    Per D-02: upsert with latest-document-wins semantics (no conflict flagging).
    Conditions from diagnoses: clinical_status="active", verification_status="confirmed"
    Conditions from suspected_diagnoses: clinical_status="suspected", verification_status="provisional"
    """
    # Confirmed diagnoses
    for dx in note.diagnoses:
        row = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "document_id": doc_id,
            "raw_condition": dx,
            "normalized_condition": dx.strip().lower(),
            "clinical_status": "active",
            "verification_status": "confirmed",
        }
        client.table("patient_conditions").upsert(
            row, on_conflict="user_id,normalized_condition"
        ).execute()

    # Suspected diagnoses
    for dx in note.suspected_diagnoses:
        row = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "document_id": doc_id,
            "raw_condition": dx,
            "normalized_condition": dx.strip().lower(),
            "clinical_status": "suspected",
            "verification_status": "provisional",
        }
        client.table("patient_conditions").upsert(
            row, on_conflict="user_id,normalized_condition"
        ).execute()

    # Allergies
    for allergy in note.allergies:
        row = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "document_id": doc_id,
            "raw_allergen": allergy,
            "normalized_allergen": allergy.strip().lower(),
            "reaction": None,
        }
        client.table("patient_allergies").upsert(
            row, on_conflict="user_id,normalized_allergen"
        ).execute()

    # Medications from clinical note (plain strings, not MedicationEntry)
    for med in note.medications:
        row = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "document_id": doc_id,
            "raw_medication": med,
            "normalized_medication": med.strip().lower(),
            "dose": None,
            "route": None,
            "frequency": None,
            "status": "active",
        }
        client.table("patient_medications").upsert(
            row, on_conflict="user_id,normalized_medication"
        ).execute()


# ── Medication document promotion ─────────────────────────────────────────────

def _promote_medications(
    client,
    doc_id: str,
    user_id: str,
    med_doc: MedicationDocument,
) -> None:
    """Promote a MedicationDocument into patient_medications.

    Per D-02: upsert with latest-document-wins. MedicationEntry has structured dose/route/frequency.
    """
    for entry in med_doc.medications:
        row = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "document_id": doc_id,
            "raw_medication": entry.name,
            "normalized_medication": entry.name.strip().lower(),
            "dose": entry.dose,
            "route": entry.route,
            "frequency": entry.frequency,
            "status": "active",
        }
        client.table("patient_medications").upsert(
            row, on_conflict="user_id,normalized_medication"
        ).execute()


# ── Imaging promotion ─────────────────────────────────────────────────────────

def _promote_imaging(
    client,
    doc_id: str,
    user_id: str,
    report: ImagingReport,
) -> None:
    """Promote an ImagingReport into patient_imaging_findings.

    Per D-13: no natural dedup key for imaging findings — use plain insert (not upsert).
    Each imaging report is a distinct finding worth preserving.
    """
    row = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "document_id": doc_id,
        "modality": report.modality,
        "body_region": report.body_region,
        "impression": report.impression,
        "urgency": report.urgency,
    }
    client.table("patient_imaging_findings").insert(row).execute()
