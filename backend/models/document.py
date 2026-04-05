from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel


class ExtractionMeta(BaseModel):
    """
    Metadata about how text was extracted from a document.
    Stored as JSONB in documents.text_extraction_meta.

    Fields match the dict returned by extract_text_with_meta() in document_intelligence.py.
    """
    method: str                        # "native" | "ocr"
    quality_score: float               # [0.0, 1.0]
    page_strategies: list[dict] = []   # per-page is_native_page() results
    library: str                       # e.g. "pymupdf/1.24.5" or "azure-ai-formrecognizer/3.3.3"
    fallback_reason: str | None = None # why native was rejected, or None
    extracted_at: str                  # ISO 8601 datetime string


class ExtractedEntity(BaseModel):
    text: str
    category: str          # Medication, Diagnosis, Symptom, etc.
    normalized_text: str | None = None
    confidence: float


# ── Structured result models per document family ──────────────────────────────

class LabFinding(BaseModel):
    name: str
    value: str
    unit: str | None = None
    reference_range: str | None = None
    flag: Literal["normal", "high", "low", "borderline", "critical"] | None = None
    is_clinically_actionable: bool = False


class StructuredLab(BaseModel):
    """Family: structured_lab — blood tests, urinalysis, hormones, biochemistry."""
    document_family: Literal["structured_lab"] = "structured_lab"
    exam_name: str | None = None
    collection_date: str | None = None
    release_date: str | None = None
    sample_type: str | None = None
    findings: list[LabFinding] = []
    summary: str | None = None
    entities_for_memory: list[str] = []


class ImagingReport(BaseModel):
    """Family: imaging_narrative — CT, MRI, ultrasound, X-ray, mammography."""
    document_family: Literal["imaging_narrative"] = "imaging_narrative"
    modality: str | None = None
    body_region: str | None = None
    indication: str | None = None
    findings: str | None = None
    impression: str | None = None
    recommendations: str | None = None
    urgency: Literal["routine", "urgent", "critical"] | None = None
    comparison_with_prior: str | None = None
    summary: str | None = None
    entities_for_memory: list[str] = []


class ClinicalNote(BaseModel):
    """Family: clinical_narrative — visit notes, discharge summaries, referrals."""
    document_family: Literal["clinical_narrative"] = "clinical_narrative"
    chief_complaint: str | None = None
    symptoms: list[str] = []
    diagnoses: list[str] = []
    suspected_diagnoses: list[str] = []
    allergies: list[str] = []
    medications: list[str] = []
    conduct: str | None = None
    follow_up: str | None = None
    specialties: list[str] = []
    summary: str | None = None
    entities_for_memory: list[str] = []


class MedicationEntry(BaseModel):
    name: str
    dose: str | None = None
    route: str | None = None
    frequency: str | None = None
    duration: str | None = None
    indication: str | None = None


class MedicationDocument(BaseModel):
    """Family: medication_document — prescriptions, medication lists."""
    document_family: Literal["medication_document"] = "medication_document"
    medications: list[MedicationEntry] = []
    summary: str | None = None
    entities_for_memory: list[str] = []


class StructuredResult(BaseModel):
    """
    Unified structured result wrapping the family-specific data.
    Stored as JSONB in Supabase `documents.structured_result`.
    """
    document_family: str  # structured_lab | imaging_narrative | clinical_narrative | medication_document | unknown
    document_subtype: str | None = None
    extraction_confidence: float = 0.0
    processing_version: str = "v2"
    admin_metadata: dict[str, Any] = {}   # cpf, crm, lab name — kept separate, never shown as clinical
    structured_data: dict[str, Any] = {}  # StructuredLab / ImagingReport / ClinicalNote / MedicationDocument
    entities_for_memory: list[str] = []
    raw_clinical_text: str | None = None  # cleaned OCR after admin removal


# ── Response / storage models ─────────────────────────────────────────────────

class DocumentMetadata(BaseModel):
    id: str
    user_id: str
    blob_url: str
    original_name: str
    file_type: Literal["pdf", "image"]
    upload_date: datetime
    entity_count: int
    document_family: str | None = None
    summary: str | None = None


class DocumentListResponse(BaseModel):
    documents: list[DocumentMetadata]
    total: int


class UploadResponse(BaseModel):
    document_id: str
    message: str
    entity_count: int
    blob_url: str
    document_family: str | None = None
    summary: str | None = None


class DocumentDetail(BaseModel):
    document_id: str
    user_id: str
    original_name: str
    upload_date: datetime
    anonymized_text: str
    medical_entities: list[ExtractedEntity]
    pii_substitutions: list[str]
    structured_result: StructuredResult | None = None
    file_blob_url: str | None = None
    text_extraction_meta: ExtractionMeta | None = None
