"""
Supabase Store — persistência real de documentos no PostgreSQL via Supabase.
Usado quando USE_MOCK_AZURE=false.

Tabela `documents`:
  id, user_id, original_name, blob_url, anonymized_text,
  medical_entities (jsonb), pii_substitutions (jsonb), upload_date
"""
import os
from datetime import datetime, timezone

from supabase import create_client, Client
from models.document import DocumentDetail, ExtractedEntity

_client: Client | None = None


def _get_client() -> Client:
    global _client
    if _client is None:
        url = os.environ["SUPABASE_URL"]
        key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
        _client = create_client(url, key)
    return _client


def save(detail: DocumentDetail) -> None:
    client = _get_client()
    client.table("documents").insert({
        "id": detail.document_id,
        "user_id": detail.user_id,
        "original_name": detail.original_name,
        "blob_url": "",
        "anonymized_text": detail.anonymized_text,
        "medical_entities": [e.model_dump() for e in detail.medical_entities],
        "pii_substitutions": detail.pii_substitutions,
        "upload_date": detail.upload_date.isoformat(),
    }).execute()


def get(doc_id: str, user_id: str) -> DocumentDetail | None:
    client = _get_client()
    res = (
        client.table("documents")
        .select("*")
        .eq("id", doc_id)
        .eq("user_id", user_id)
        .single()
        .execute()
    )
    if not res.data:
        return None
    return _row_to_detail(res.data)


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


def _row_to_detail(row: dict) -> DocumentDetail:
    return DocumentDetail(
        document_id=row["id"],
        user_id=row["user_id"],
        original_name=row["original_name"],
        upload_date=datetime.fromisoformat(row["upload_date"]),
        anonymized_text=row["anonymized_text"],
        medical_entities=[ExtractedEntity(**e) for e in (row["medical_entities"] or [])],
        pii_substitutions=row["pii_substitutions"] or [],
    )
