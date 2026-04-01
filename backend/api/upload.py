"""
POST /upload — receives a medical document and runs the hybrid pipeline:
  1. OCR (Document Intelligence)
  2. Document classification (family: lab, imaging, clinical, medication, unknown)
  3. Admin/clinical text separation
  4. Family-specific structured extraction via LLM
  5. Entity building from structured result
  6. Blob Storage upload
  7. Azure AI Search indexation (RAG)
  8. Supabase persistence
"""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from models.document import DocumentDetail, UploadResponse
from services.azure.blob_storage import upload_blob
from services.document_store import save as store_save
from services.pipeline import orchestrator
from services.rag.indexer import index_after_upload
from utils.auth import get_current_user

router = APIRouter()

ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/tiff",
    "image/webp",
}

MAX_FILE_SIZE_MB = 10


@router.post("/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user),
):
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Tipo de arquivo não suportado: {file.content_type}. Use PDF ou imagem.",
        )

    file_bytes = await file.read()

    if len(file_bytes) > MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail=f"Arquivo muito grande. Máximo: {MAX_FILE_SIZE_MB}MB.",
        )

    try:
        result = orchestrator.run(file_bytes, file.filename or "document")

        doc_id = str(uuid.uuid4())
        blob_url = upload_blob(
            file_bytes=result.raw_text.encode("utf-8"),
            filename=f"{doc_id}.txt",
            user_id=user_id,
        )

        index_after_upload(
            doc_id=doc_id,
            user_id=user_id,
            anonymized_text=result.raw_text,
            source_name=file.filename or "document",
            entities=result.entities,
        )

        store_save(DocumentDetail(
            document_id=doc_id,
            user_id=user_id,
            original_name=file.filename or "document",
            upload_date=datetime.now(timezone.utc),
            anonymized_text=result.raw_text,
            medical_entities=result.entities,
            pii_substitutions=[],
            structured_result=result.structured_result,
        ))

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar documento: {e}")

    family = result.structured_result.document_family
    entity_count = len(result.entities)

    return UploadResponse(
        document_id=doc_id,
        message=f"Documento processado ({family}). {entity_count} achados clínicos identificados.",
        entity_count=entity_count,
        blob_url=blob_url,
        document_family=family,
        summary=result.summary,
    )
