"""
Health Store — manual health entries (medications, complaints, allergies).

Supabase table: health_entries
  id, user_id, entry_type, name, details, started_at, ended_at, active, created_at

Dual-writes to patient_medications / patient_conditions / patient_allergies so that
patient_query.py (Phase 6) can surface manually entered data without re-running migration.
"""
import logging
import os
import uuid
from datetime import datetime, timezone

from supabase import create_client, Client
from models.health import HealthEntry, HealthEntryCreate, HealthEntryType

_log = logging.getLogger(__name__)

_client: Client | None = None


def _get_client() -> Client:
    global _client
    if _client is None:
        _client = create_client(
            os.environ["SUPABASE_URL"],
            os.environ["SUPABASE_SERVICE_ROLE_KEY"],
        )
    return _client


def create(user_id: str, entry: HealthEntryCreate) -> HealthEntry:
    client = _get_client()
    row = {
        "user_id": user_id,
        "entry_type": entry.entry_type.value,
        "name": entry.name,
        "details": entry.details,
        "started_at": entry.started_at.isoformat() if entry.started_at else None,
        "ended_at": entry.ended_at.isoformat() if entry.ended_at else None,
        "active": True,
    }
    res = client.table("health_entries").insert(row).execute()
    created = _row_to_entry(res.data[0])
    _sync_to_patient_table(user_id, created)
    return created


def list_by_user(user_id: str) -> list[HealthEntry]:
    client = _get_client()
    res = (
        client.table("health_entries")
        .select("*")
        .eq("user_id", user_id)
        .eq("active", True)
        .order("created_at", desc=True)
        .execute()
    )
    return [_row_to_entry(r) for r in (res.data or [])]


def delete(entry_id: str, user_id: str) -> None:
    client = _get_client()
    # Fetch entry before deleting so we can clean up the patient table too
    res = client.table("health_entries").select("*").eq("id", entry_id).eq("user_id", user_id).execute()
    entry = _row_to_entry(res.data[0]) if res.data else None
    client.table("health_entries").delete().eq("id", entry_id).eq("user_id", user_id).execute()
    if entry:
        _remove_from_patient_table(user_id, entry)


def _sync_to_patient_table(user_id: str, entry: HealthEntry) -> None:
    """Dual-write a health entry into the corresponding patient table (best-effort)."""
    try:
        client = _get_client()
        if entry.entry_type in (HealthEntryType.medication_current, HealthEntryType.medication_past):
            status = "active" if entry.entry_type == HealthEntryType.medication_current else "stopped"
            client.table("patient_medications").upsert(
                {
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "document_id": None,
                    "raw_medication": entry.name,
                    "normalized_medication": entry.name.strip().lower(),
                    "dose": entry.details,
                    "route": None,
                    "frequency": None,
                    "status": status,
                },
                on_conflict="user_id,normalized_medication",
            ).execute()
        elif entry.entry_type == HealthEntryType.complaint:
            client.table("patient_conditions").upsert(
                {
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "document_id": None,
                    "raw_condition": entry.name,
                    "normalized_condition": entry.name.strip().lower(),
                    "clinical_status": "active",
                    "verification_status": None,
                },
                on_conflict="user_id,normalized_condition",
            ).execute()
        elif entry.entry_type == HealthEntryType.allergy:
            client.table("patient_allergies").upsert(
                {
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "document_id": None,
                    "raw_allergen": entry.name,
                    "normalized_allergen": entry.name.strip().lower(),
                    "reaction": entry.details,
                },
                on_conflict="user_id,normalized_allergen",
            ).execute()
    except Exception as exc:
        _log.warning("patient table sync failed user_id=%s entry_type=%s: %s", user_id, entry.entry_type, exc)


def _remove_from_patient_table(user_id: str, entry: HealthEntry) -> None:
    """Remove or deactivate the patient table row corresponding to a deleted health entry."""
    try:
        client = _get_client()
        norm = entry.name.strip().lower()
        if entry.entry_type in (HealthEntryType.medication_current, HealthEntryType.medication_past):
            client.table("patient_medications").delete().eq("user_id", user_id).eq("normalized_medication", norm).eq("document_id", None).execute()
        elif entry.entry_type == HealthEntryType.complaint:
            client.table("patient_conditions").delete().eq("user_id", user_id).eq("normalized_condition", norm).eq("document_id", None).execute()
        elif entry.entry_type == HealthEntryType.allergy:
            client.table("patient_allergies").delete().eq("user_id", user_id).eq("normalized_allergen", norm).eq("document_id", None).execute()
    except Exception as exc:
        _log.warning("patient table removal failed user_id=%s entry_type=%s: %s", user_id, entry.entry_type, exc)


def reindex_for_rag(user_id: str) -> None:
    """Rebuild the synthetic RAG document for this user's manual health entries."""
    from services.rag.indexer import index_after_upload

    entries = list_by_user(user_id)

    medications = [e for e in entries if e.entry_type == HealthEntryType.medication_current]
    past_meds   = [e for e in entries if e.entry_type == HealthEntryType.medication_past]
    complaints  = [e for e in entries if e.entry_type == HealthEntryType.complaint]
    allergies   = [e for e in entries if e.entry_type == HealthEntryType.allergy]

    lines: list[str] = ["=== Perfil de saúde inserido manualmente pelo paciente ===\n"]

    if medications:
        items = "; ".join(f"{e.name}" + (f" ({e.details})" if e.details else "") for e in medications)
        lines.append(f"Medicamentos em uso atual: {items}.")

    if past_meds:
        items = "; ".join(f"{e.name}" + (f" ({e.details})" if e.details else "") for e in past_meds)
        lines.append(f"Medicamentos de uso anterior: {items}.")

    if complaints:
        items = "; ".join(f"{e.name}" + (f" — {e.details}" if e.details else "") for e in complaints)
        lines.append(f"Queixas recentes relatadas pelo paciente: {items}.")

    if allergies:
        items = "; ".join(f"{e.name}" + (f" (reação: {e.details})" if e.details else "") for e in allergies)
        lines.append(f"Alergias informadas pelo paciente: {items}.")

    if not (medications or past_meds or complaints or allergies):
        lines.append("Nenhuma entrada manual registrada.")

    text = "\n".join(lines)

    index_after_upload(
        doc_id=f"manual_{user_id}",
        user_id=user_id,
        anonymized_text=text,
        source_name="Perfil de saúde manual",
        entities=[],
    )


def _row_to_entry(row: dict) -> HealthEntry:
    return HealthEntry(
        id=row["id"],
        user_id=row["user_id"],
        entry_type=HealthEntryType(row["entry_type"]),
        name=row["name"],
        details=row.get("details"),
        started_at=row.get("started_at"),
        ended_at=row.get("ended_at"),
        active=row.get("active", True),
        created_at=datetime.fromisoformat(row["created_at"]) if row.get("created_at") else datetime.now(timezone.utc),
    )
