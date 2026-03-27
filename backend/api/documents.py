"""
GET /documents          — lista documentos do usuário autenticado.
GET /documents/{doc_id} — detalhe de um documento: texto anonimizado + entidades extraídas.
"""
from fastapi import APIRouter, Depends, HTTPException

from models.document import DocumentDetail, DocumentListResponse, DocumentMetadata
from services.document_store import get as store_get, list_by_user
from utils.auth import get_current_user

router = APIRouter()


@router.get("/documents", response_model=DocumentListResponse)
def list_documents(user_id: str = Depends(get_current_user)):
    docs = list_by_user(user_id)

    metadata = [
        DocumentMetadata(
            id=d.document_id,
            user_id=d.user_id,
            blob_url="",
            original_name=d.original_name,
            file_type="pdf",
            upload_date=d.upload_date,
            entity_count=len(d.medical_entities),
            anonymized=True,
        )
        for d in docs
    ]

    return DocumentListResponse(documents=metadata, total=len(metadata))


@router.get("/documents/{doc_id}", response_model=DocumentDetail)
def get_document(doc_id: str, user_id: str = Depends(get_current_user)):
    doc = store_get(doc_id, user_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado.")
    return doc
