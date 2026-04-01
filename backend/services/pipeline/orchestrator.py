"""
Pipeline orchestrator — unified entry point for document processing.

Flow:
  1. OCR (Document Intelligence) → raw_text
  2. Classify document family (classifier)
  3. Separate admin metadata from clinical text (cleaner)
  4. Extract structured data per family (extractor, LLM-based)
  5. Build entity list for RAG/memory from structured result
  6. NER fallback via Text Analytics for Health (only for unknown family)

Returns a PipelineResult with all data needed for storage, RAG, and UI.
"""

from dataclasses import dataclass, field

from models.document import ExtractedEntity, StructuredResult
from services.azure.document_intelligence import extract_text
from services.pipeline.classifier import classify
from services.pipeline.cleaner import clean
from services.pipeline.extractor import extract_structured


@dataclass
class PipelineResult:
    raw_text: str
    structured_result: StructuredResult
    entities: list[ExtractedEntity]      # for legacy RAG/search compatibility
    summary: str | None = None


def _build_entities_from_structured(structured_data: dict, document_family: str) -> list[ExtractedEntity]:
    """
    Derive ExtractedEntity list from the structured result.
    Only includes clinically actionable items.
    """
    entities: list[ExtractedEntity] = []

    if document_family == "structured_lab":
        for finding in structured_data.get("findings", []):
            if finding.get("is_clinically_actionable") and finding.get("flag") not in (None, "normal"):
                entities.append(ExtractedEntity(
                    text=f"{finding['name']}: {finding['value']}{' ' + finding['unit'] if finding.get('unit') else ''}".strip(),
                    category="LabFinding",
                    normalized_text=finding.get("name"),
                    confidence=0.95,
                ))

    elif document_family == "imaging_narrative":
        impression = structured_data.get("impression") or structured_data.get("findings", "")
        if impression:
            entities.append(ExtractedEntity(
                text=impression[:200],
                category="ImagingImpression",
                normalized_text=None,
                confidence=0.90,
            ))
        for mem in structured_data.get("entities_for_memory", []):
            entities.append(ExtractedEntity(
                text=mem,
                category="ImagingFinding",
                normalized_text=None,
                confidence=0.88,
            ))

    elif document_family == "clinical_narrative":
        for dx in structured_data.get("diagnoses", []):
            entities.append(ExtractedEntity(text=dx, category="Diagnosis", normalized_text=None, confidence=0.90))
        for sx in structured_data.get("symptoms", []):
            entities.append(ExtractedEntity(text=sx, category="SymptomOrSign", normalized_text=None, confidence=0.85))
        for al in structured_data.get("allergies", []):
            entities.append(ExtractedEntity(text=al, category="AllergyEntity", normalized_text=None, confidence=0.92))
        for med in structured_data.get("medications", []):
            entities.append(ExtractedEntity(text=med, category="MedicationName", normalized_text=None, confidence=0.90))

    elif document_family == "medication_document":
        for med in structured_data.get("medications", []):
            name = med.get("name", "")
            dose = med.get("dose", "")
            text = f"{name} {dose}".strip() if dose else name
            entities.append(ExtractedEntity(text=text, category="MedicationName", normalized_text=name, confidence=0.92))

    return entities


def _ner_fallback(clinical_text: str) -> list[ExtractedEntity]:
    """Use Text Analytics for Health as fallback for unknown documents."""
    try:
        from services.azure.text_analytics import extract_health_entities
        return extract_health_entities(clinical_text)
    except Exception:
        return []


def run(file_bytes: bytes, filename: str) -> PipelineResult:
    """
    Run the full document understanding pipeline.

    Args:
        file_bytes: raw file bytes (PDF or image)
        filename: original filename

    Returns:
        PipelineResult with structured data, entities, and summary
    """
    # Step 1: OCR
    raw_text = extract_text(file_bytes, filename)

    # Step 2: Classify
    document_family, confidence = classify(raw_text)

    # Step 3: Clean — separate admin from clinical
    clean_result = clean(raw_text)
    clinical_text = clean_result.clinical_text
    admin_metadata = clean_result.admin_metadata

    # Step 4: Structured extraction
    structured_data = extract_structured(clinical_text, document_family)

    # Step 5: Build entities
    if document_family == "unknown":
        entities = _ner_fallback(clinical_text)
        entities_for_memory: list[str] = [e.text for e in entities[:10]]
    else:
        entities = _build_entities_from_structured(structured_data, document_family)
        entities_for_memory = structured_data.get("entities_for_memory", [])

    # Step 6: Summary
    summary = structured_data.get("summary")

    structured_result = StructuredResult(
        document_family=document_family,
        extraction_confidence=confidence,
        processing_version="v2",
        admin_metadata=admin_metadata,
        structured_data=structured_data,
        entities_for_memory=entities_for_memory,
        raw_clinical_text=clinical_text,
    )

    return PipelineResult(
        raw_text=raw_text,
        structured_result=structured_result,
        entities=entities,
        summary=summary,
    )
