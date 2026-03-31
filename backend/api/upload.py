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
from services.anonymizer.pipeline import run_pipeline
from services.azure.blob_storage import upload_blob
from services.azure.document_intelligence import extract_text
from services.azure.text_analytics import PII_CATEGORIES, extract_health_entities
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

        # 2. Extração de entidades
        logging.warning("UPLOAD: iniciando extração de entidades")
        entities = extract_health_entities(raw_text)
        logging.warning("UPLOAD: entidades extraídas")

        # 3. Anonimização
        anonymized_text, substitutions = run_pipeline(raw_text, entities)

        # 4. Upload do texto anonimizado (não do arquivo original)
        doc_id = str(uuid.uuid4())
        anon_filename = f"{doc_id}_anonymized.txt"
        logging.warning("UPLOAD: iniciando blob upload")
        blob_url = upload_blob(
            file_bytes=anonymized_text.encode("utf-8"),
            filename=anon_filename,
            user_id=user_id,
        )
        logging.warning("UPLOAD: blob upload concluído")

        medical_entities = [e for e in entities if e.category not in PII_CATEGORIES]

        # 5. Indexação no Azure AI Search para RAG
        index_after_upload(
            doc_id=doc_id,
            user_id=user_id,
            anonymized_text=anonymized_text,
            source_name=file.filename or "document",
            entities=medical_entities,
        )

        # 6. Persistência no Supabase
        store_save(DocumentDetail(
            document_id=doc_id,
            user_id=user_id,
            original_name=file.filename or "document",
            upload_date=datetime.now(timezone.utc),
            anonymized_text=anonymized_text,
            medical_entities=medical_entities,
            pii_substitutions=substitutions,
        ))

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar documento: {e}")

    return UploadResponse(
        document_id=doc_id,
        message=f"Documento processado com sucesso. {len(substitutions)} substituições de PII realizadas.",
        entity_count=len(medical_entities),
        blob_url=blob_url,
    )
