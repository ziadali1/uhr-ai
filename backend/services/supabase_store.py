"""
Supabase Store — persistência real de documentos no PostgreSQL via Supabase.

Tabela `documents`:
  id, user_id, original_name, blob_url, anonymized_text,
  medical_entities (jsonb), pii_substitutions (jsonb),
  structured_result (jsonb), upload_date
"""
import os
from datetime import datetime, timezone

from supabase import create_client, Client
from models.document import DocumentDetail, ExtractedEntity, StructuredResult, ExtractionMeta

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
    row: dict = {
        "id": detail.document_id,
        "user_id": detail.user_id,
        "original_name": detail.original_name,
        "blob_url": "",
        "anonymized_text": detail.anonymized_text,
        "medical_entities": [e.model_dump() for e in detail.medical_entities],
        "pii_substitutions": detail.pii_substitutions,
        "upload_date": detail.upload_date.isoformat(),
        "file_blob_url": detail.file_blob_url,
    }
    if detail.structured_result is not None:
        row["structured_result"] = detail.structured_result.model_dump()
    try:
        # Column added in Phase 1 migration — see .planning/phases/01-adaptive-text-extraction/
        if detail.text_extraction_meta is not None:
            row["text_extraction_meta"] = detail.text_extraction_meta.model_dump()
    except Exception:
        pass  # column may not exist yet; migration required
    client.table("documents").insert(row).execute()


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
    structured_result = None
    if row.get("structured_result"):
        try:
            structured_result = StructuredResult(**row["structured_result"])
        except Exception:
            pass

    text_extraction_meta = None
    if row.get("text_extraction_meta"):
        try:
            text_extraction_meta = ExtractionMeta(**row["text_extraction_meta"])
        except Exception:
            pass

    return DocumentDetail(
        document_id=row["id"],
        user_id=row["user_id"],
        original_name=row["original_name"],
        upload_date=datetime.fromisoformat(row["upload_date"]),
        anonymized_text=row["anonymized_text"],
        medical_entities=[ExtractedEntity(**e) for e in (row["medical_entities"] or [])],
        pii_substitutions=row["pii_substitutions"] or [],
        structured_result=structured_result,
        file_blob_url=row.get("file_blob_url"),
        text_extraction_meta=text_extraction_meta,
    )
