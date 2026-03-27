"""
POST /upload — recebe documento médico e executa o pipeline completo:
  1. OCR (Document Intelligence)
  2. Extração de entidades (Text Analytics for Health)
  3. Anonimização (pipeline)
  4. Upload no Blob Storage (versão anonimizada)
  5. Retorna metadados do documento processado
"""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from models.document import UploadResponse
from services.anonymizer.pipeline import run_pipeline
from services.azure.blob_storage import upload_blob
from services.azure.document_intelligence import extract_text
from services.azure.text_analytics import extract_health_entities
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

    # 1. OCR
    raw_text = extract_text(file_bytes, file.filename or "document")

    # 2. Extração de entidades
    entities = extract_health_entities(raw_text)

    # 3. Anonimização
    anonymized_text, substitutions = run_pipeline(raw_text, entities)

    # 4. Upload do texto anonimizado (não do arquivo original)
    doc_id = str(uuid.uuid4())
    anon_filename = f"{doc_id}_anonymized.txt"
    blob_url = upload_blob(
        file_bytes=anonymized_text.encode("utf-8"),
        filename=anon_filename,
        user_id=user_id,
    )

    # Conta apenas entidades médicas (não PII)
    medical_entity_count = sum(
        1 for e in entities
        if e.category not in {"PersonName", "PersonId", "MedicalRegistration", "Address", "PhoneNumber"}
    )

    return UploadResponse(
        document_id=doc_id,
        message=f"Documento processado com sucesso. {len(substitutions)} substituições de PII realizadas.",
        entity_count=medical_entity_count,
        blob_url=blob_url,
    )
