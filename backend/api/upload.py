"""
POST /upload — recebe documento médico e executa o pipeline híbrido:
  1. Upload do arquivo original no Blob Storage
  2. OCR + classificação + limpeza + extração estruturada (pipeline v2)
  3. Indexação no Azure AI Search (RAG)
  4. Persistência no Supabase (texto + resultado estruturado + URL do original)
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

_EXT_MAP = {
    "application/pdf": "pdf",
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/tiff": "tiff",
    "image/webp": "webp",
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

    doc_id = str(uuid.uuid4())

    try:
        # 1. Store original file in blob (before pipeline — preserves original regardless of errors)
        ext = _EXT_MAP.get(file.content_type or "", "bin")
        file_blob_url = upload_blob(
            file_bytes=file_bytes,
            filename=f"{doc_id}_original.{ext}",
            user_id=user_id,
        )

        # 2. Run hybrid pipeline (OCR → classify → clean → LLM extract → entities)
        result = orchestrator.run(file_bytes, file.filename or "document")

        # 3. Store OCR text blob (for RAG retrieval)
        upload_blob(
            file_bytes=result.raw_text.encode("utf-8"),
            filename=f"{doc_id}.txt",
            user_id=user_id,
        )

        # 4. Index in Azure AI Search
        index_after_upload(
            doc_id=doc_id,
            user_id=user_id,
            anonymized_text=result.raw_text,
            source_name=file.filename or "document",
            entities=result.entities,
        )

        # 5. Persist to Supabase
        store_save(DocumentDetail(
            document_id=doc_id,
            user_id=user_id,
            original_name=file.filename or "document",
            upload_date=datetime.now(timezone.utc),
            anonymized_text=result.raw_text,
            medical_entities=result.entities,
            pii_substitutions=[],
            structured_result=result.structured_result,
            file_blob_url=file_blob_url,
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
        blob_url=file_blob_url,
        document_family=family,
        summary=result.summary,
    )
