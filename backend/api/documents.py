"""
GET /documents               — lista documentos do usuário autenticado.
GET /documents/{doc_id}      — detalhe: texto + entidades + resultado estruturado.
GET /documents/{doc_id}/file — proxy que devolve o arquivo original (PDF/imagem).
"""
import mimetypes
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from models.document import DocumentDetail, DocumentListResponse, DocumentMetadata
from services.azure.blob_storage import download_blob
from services.document_store import get as store_get, list_by_user
from utils.auth import get_current_user

router = APIRouter()


@router.get("/documents", response_model=DocumentListResponse)
def list_documents(user_id: str = Depends(get_current_user)):
    docs = list_by_user(user_id)

    metadata = []
    for d in docs:
        family = d.structured_result.document_family if d.structured_result else None
        summary = None
        if d.structured_result and d.structured_result.structured_data:
            summary = d.structured_result.structured_data.get("summary")

        metadata.append(DocumentMetadata(
            id=d.document_id,
            user_id=d.user_id,
            blob_url="",
            original_name=d.original_name,
            file_type="pdf",
            upload_date=d.upload_date,
            entity_count=len(d.medical_entities),
            document_family=family,
            summary=summary,
        ))

    return DocumentListResponse(documents=metadata, total=len(metadata))


@router.get("/documents/{doc_id}", response_model=DocumentDetail)
def get_document(doc_id: str, user_id: str = Depends(get_current_user)):
    doc = store_get(doc_id, user_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado.")
    return doc


@router.get("/documents/{doc_id}/file")
def get_document_file(doc_id: str, user_id: str = Depends(get_current_user)):
    """Proxy: devolve o arquivo original (PDF/imagem) ao browser."""
    doc = store_get(doc_id, user_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado.")
    if not doc.file_blob_url:
        raise HTTPException(status_code=404, detail="Arquivo original não disponível.")

    file_bytes = download_blob(doc.file_blob_url)

    # Derive content type from the stored blob filename
    content_type = "application/octet-stream"
    url = doc.file_blob_url
    if url.endswith(".pdf"):
        content_type = "application/pdf"
    elif url.endswith((".jpg", ".jpeg")):
        content_type = "image/jpeg"
    elif url.endswith(".png"):
        content_type = "image/png"
    elif url.endswith(".tiff") or url.endswith(".tif"):
        content_type = "image/tiff"

    return Response(
        content=file_bytes,
        media_type=content_type,
        headers={"Content-Disposition": f'inline; filename="{doc.original_name}"'},
    )
