"""
Context block assembly — builds a plain-text embedding input from StructuredResult.

Per D-01/D-04: embed structured context block, NOT anonymized_text.
Per D-02: assembly order: summary -> entities_for_memory -> family-specific fields.
Per D-03: fallback to first 1000 chars of anonymized_text if sr is None or empty.
Per D-04: plain text, newline-separated, max 2000 chars.
"""
from models.document import (
    StructuredResult,
    StructuredLab,
    ImagingReport,
    ClinicalNote,
    MedicationDocument,
)


def assemble_context_block(sr: StructuredResult | None, anonymized_text: str) -> str:
    """Build a plain-text context block from StructuredResult for embedding.

    Args:
        sr: The structured result from document extraction, or None.
        anonymized_text: Fallback text if sr is None or empty.

    Returns:
        A plain-text string of max 2000 chars for embedding.
    """
    if sr is None:
        return anonymized_text[:1000]

    parts: list[str] = []

    # Top-level entities
    for entity in sr.entities_for_memory:
        if entity:
            parts.append(entity)

    # Dispatch on document family
    try:
        if sr.document_family == "structured_lab":
            lab = StructuredLab(**sr.structured_data)
            if lab.summary:
                parts.append(lab.summary)
            for entity in lab.entities_for_memory:
                if entity:
                    parts.append(entity)
            for f in lab.findings:
                line = f"{f.name}: {f.value}"
                if f.unit:
                    line += f" {f.unit}"
                if f.flag:
                    line += f" [{f.flag}]"
                parts.append(line)

        elif sr.document_family == "imaging_narrative":
            report = ImagingReport(**sr.structured_data)
            if report.summary:
                parts.append(report.summary)
            for entity in report.entities_for_memory:
                if entity:
                    parts.append(entity)
            if report.impression:
                parts.append(report.impression)
            if report.findings:
                parts.append(report.findings)

        elif sr.document_family == "clinical_narrative":
            note = ClinicalNote(**sr.structured_data)
            if note.summary:
                parts.append(note.summary)
            for entity in note.entities_for_memory:
                if entity:
                    parts.append(entity)
            for diagnosis in note.diagnoses:
                if diagnosis:
                    parts.append(diagnosis)
            for symptom in note.symptoms:
                if symptom:
                    parts.append(symptom)
            for allergy in note.allergies:
                if allergy:
                    parts.append(allergy)
            for medication in note.medications:
                if medication:
                    parts.append(medication)

        elif sr.document_family == "medication_document":
            med_doc = MedicationDocument(**sr.structured_data)
            if med_doc.summary:
                parts.append(med_doc.summary)
            for entity in med_doc.entities_for_memory:
                if entity:
                    parts.append(entity)
            for entry in med_doc.medications:
                line = entry.name
                if entry.dose:
                    line += f" {entry.dose}"
                parts.append(line)

    except Exception:
        # Pitfall 3: partial/malformed structured_data is fine — use what we have
        pass

    block = "\n".join(p for p in parts if p)

    if not block.strip():
        return anonymized_text[:1000]

    return block[:2000]
