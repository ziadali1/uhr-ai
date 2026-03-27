"""
Document Store — fachada que roteia para o store correto:
  USE_MOCK_AZURE=true  → memória (desenvolvimento local)
  USE_MOCK_AZURE=false → Supabase PostgreSQL (produção)
"""
import os
from datetime import datetime, timezone
from models.document import DocumentDetail, ExtractedEntity

# Store em memória (mock)
_store: dict[str, DocumentDetail] = {}


def _use_mock() -> bool:
    return os.getenv("USE_MOCK_AZURE", "true").lower() == "true"


def save(detail: DocumentDetail) -> None:
    if _use_mock():
        _store[detail.document_id] = detail
        return
    from services.supabase_store import save as sb_save
    sb_save(detail)


def get(doc_id: str, user_id: str) -> DocumentDetail | None:
    if _use_mock():
        doc = _store.get(doc_id)
        return doc if doc and doc.user_id == user_id else None
    from services.supabase_store import get as sb_get
    return sb_get(doc_id, user_id)


def list_by_user(user_id: str) -> list[DocumentDetail]:
    if _use_mock():
        return [d for d in _store.values() if d.user_id == user_id]
    from services.supabase_store import list_by_user as sb_list
    return sb_list(user_id)
