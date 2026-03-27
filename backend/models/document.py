from datetime import datetime
from typing import Literal
from pydantic import BaseModel


class DocumentMetadata(BaseModel):
    id: str
    user_id: str
    blob_url: str
    original_name: str
    file_type: Literal["pdf", "image"]
    upload_date: datetime
    entity_count: int
    anonymized: bool = True


class DocumentListResponse(BaseModel):
    documents: list[DocumentMetadata]
    total: int


class UploadResponse(BaseModel):
    document_id: str
    message: str
    entity_count: int
    blob_url: str


class ExtractedEntity(BaseModel):
    text: str
    category: str          # Medication, Diagnosis, Symptom, etc.
    normalized_text: str | None = None
    confidence: float
