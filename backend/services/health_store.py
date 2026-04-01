"""
Health Store — manual health entries (medications, complaints, allergies).

Supabase table: health_entries
  id, user_id, entry_type, name, details, started_at, ended_at, active, created_at
"""
import os
from datetime import datetime, timezone

from supabase import create_client, Client
from models.health import HealthEntry, HealthEntryCreate, HealthEntryType

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
    return _row_to_entry(res.data[0])


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
    client.table("health_entries").delete().eq("id", entry_id).eq("user_id", user_id).execute()


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
