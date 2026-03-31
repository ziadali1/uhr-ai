"""
POST /upload — recebe documento médico e executa o pipeline completo:
  1. OCR (Document Intelligence)
  2. Extração de entidades (Text Analytics for Health)
  3. Anonimização (pipeline)
  4. Upload no Blob Storage (versão anonimizada)
  5. Indexação no Azure AI Search (RAG)
  6. Retorna metadados do documento processado
"""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from models.document import DocumentDetail, UploadResponse
from services.azure.blob_storage import upload_blob
from services.azure.document_intelligence import extract_text
from services.azure.text_analytics import extract_health_entities
from services.document_store import save as store_save
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
    # Validação de tipo
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Tipo de arquivo não suportado: {file.content_type}. Use PDF ou imagem.",
        )

    file_bytes = await file.read()

    # Validação de tamanho
    if len(file_bytes) > MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail=f"Arquivo muito grande. Máximo: {MAX_FILE_SIZE_MB}MB.",
        )

    try:
        # 1. OCR
        import logging
        logging.warning("UPLOAD: iniciando OCR")
        raw_text = extract_text(file_bytes, file.filename or "document")
        logging.warning("UPLOAD: OCR concluído")

        # 2. Extração de entidades clínicas
        logging.warning("UPLOAD: iniciando extração de entidades")
        entities = extract_health_entities(raw_text)
        logging.warning("UPLOAD: entidades extraídas")

        # 3. Upload do texto completo (sem anonimização — usuário consentiu)
        doc_id = str(uuid.uuid4())
        txt_filename = f"{doc_id}.txt"
        logging.warning("UPLOAD: iniciando blob upload")
        blob_url = upload_blob(
            file_bytes=raw_text.encode("utf-8"),
            filename=txt_filename,
            user_id=user_id,
        )
        logging.warning("UPLOAD: blob upload concluído")

        # 4. Indexação no Azure AI Search para RAG
        index_after_upload(
            doc_id=doc_id,
            user_id=user_id,
            anonymized_text=raw_text,
            source_name=file.filename or "document",
            entities=entities,
        )

        # 5. Persistência no Supabase
        store_save(DocumentDetail(
            document_id=doc_id,
            user_id=user_id,
            original_name=file.filename or "document",
            upload_date=datetime.now(timezone.utc),
            anonymized_text=raw_text,
            medical_entities=entities,
            pii_substitutions=[],
        ))

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar documento: {e}")

    return UploadResponse(
        document_id=doc_id,
        message=f"Documento processado com sucesso. {len(entities)} entidades clínicas identificadas.",
        entity_count=len(entities),
        blob_url=blob_url,
    )
