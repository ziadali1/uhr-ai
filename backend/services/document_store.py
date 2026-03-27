"""
Store em memória para metadados de documentos processados.
Na Fase 5 será substituído por tabela no Supabase/PostgreSQL.
"""
from datetime import datetime, timezone
from models.document import DocumentDetail, ExtractedEntity

# doc_id → DocumentDetail
_store: dict[str, DocumentDetail] = {}


def save(detail: DocumentDetail) -> None:
    _store[detail.document_id] = detail


def get(doc_id: str, user_id: str) -> DocumentDetail | None:
    doc = _store.get(doc_id)
    if doc and doc.user_id == user_id:
        return doc
    return None


def list_by_user(user_id: str) -> list[DocumentDetail]:
    return [d for d in _store.values() if d.user_id == user_id]
