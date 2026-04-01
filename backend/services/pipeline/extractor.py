"""
Family-specific structured extraction via LLM.

Each family has a dedicated prompt that instructs Claude to return a strict JSON
schema. Mock mode returns realistic per-family examples for development.

Families:
  structured_lab       → StructuredLab schema
  imaging_narrative    → ImagingReport schema
  clinical_narrative   → ClinicalNote schema
  medication_document  → MedicationDocument schema
  unknown              → minimal extraction, NER fallback
"""

import json
import logging
import re

logger = logging.getLogger(__name__)


# ── Prompt templates per family ───────────────────────────────────────────────

_SYSTEM_BASE = (
    "You are a clinical document understanding assistant. "
    "You extract structured information from medical document text. "
    "Respond ONLY with valid JSON matching the schema provided. "
    "Do not include any explanation, markdown fences, or extra text. "
    "If a field cannot be determined from the text, use null. "
    "Never invent values. Use the original language (Portuguese) for text fields."
)

_PROMPTS: dict[str, str] = {
    "structured_lab": """
Extract all laboratory findings from the clinical text below.

Return JSON with this exact schema:
{
  "exam_name": "string or null",
  "collection_date": "ISO datetime string or null",
  "release_date": "ISO datetime string or null",
  "sample_type": "string or null",
  "findings": [
    {
      "name": "analyte name",
      "value": "measured value as string",
      "unit": "unit string or null",
      "reference_range": "reference range as string or null",
      "flag": "normal|high|low|borderline|critical or null",
      "is_clinically_actionable": true or false
    }
  ],
  "summary": "1-3 sentence clinical summary focusing on abnormal/relevant findings",
  "entities_for_memory": ["list of clinically relevant strings for patient memory"]
}

Rules for flag:
- normal: value within reference range
- high: above upper limit
- low: below lower limit
- borderline: near limits or qualitative terms like 'discreta', 'leve', 'rara'
- critical: critically abnormal (panic values)

Rules for is_clinically_actionable:
- true only if flag is high/low/borderline/critical
- false for normal results

Rules for entities_for_memory:
- Include only actionable findings (flag != normal)
- Write as short clinical phrases in Portuguese
- Do NOT include: analyte names with normal values, section headers, method names

TEXT TO ANALYZE:
""",

    "imaging_narrative": """
Extract structured information from the imaging report text below.

Return JSON with this exact schema:
{
  "modality": "CT|MRI|ultrasound|X-ray|mammography|PET|other or null",
  "body_region": "body region examined or null",
  "indication": "clinical indication or null",
  "findings": "free text describing all imaging findings",
  "impression": "final impression/conclusion or null",
  "recommendations": "recommendations or follow-up suggested or null",
  "urgency": "routine|urgent|critical or null",
  "comparison_with_prior": "comparison with prior study if mentioned or null",
  "summary": "1-2 sentence summary of the most clinically relevant findings",
  "entities_for_memory": ["clinically relevant findings for patient memory"]
}

For urgency:
- critical: requires immediate action (e.g., pneumothorax, fracture, hemorrhage)
- urgent: needs prompt attention within 24-48h
- routine: elective or incidental findings

For entities_for_memory: include abnormal findings, diagnoses mentioned, significant incidental findings.
Do NOT include: normal findings unless explicitly relevant, technique details, patient positioning.

TEXT TO ANALYZE:
""",

    "clinical_narrative": """
Extract structured clinical information from the medical note below.

Return JSON with this exact schema:
{
  "chief_complaint": "main complaint or reason for visit or null",
  "symptoms": ["list of reported symptoms"],
  "diagnoses": ["confirmed diagnoses mentioned"],
  "suspected_diagnoses": ["suspected or differential diagnoses"],
  "allergies": ["allergies mentioned, with reaction if available"],
  "medications": ["medications mentioned with dose if available"],
  "conduct": "clinical conduct/plan described or null",
  "follow_up": "follow-up instructions or referrals or null",
  "specialties": ["medical specialties involved or referred"],
  "summary": "2-3 sentence clinical summary",
  "entities_for_memory": ["most important clinical facts for patient memory"]
}

For entities_for_memory: prioritize diagnoses, active medications, allergies, chronic conditions.
Do NOT include: normal exam findings, routine instructions, administrative data.

TEXT TO ANALYZE:
""",

    "medication_document": """
Extract all medications from the prescription or medication list below.

Return JSON with this exact schema:
{
  "medications": [
    {
      "name": "medication name",
      "dose": "dose string or null",
      "route": "route of administration or null",
      "frequency": "frequency or null",
      "duration": "duration or null",
      "indication": "indication if mentioned or null"
    }
  ],
  "summary": "brief summary of the prescription",
  "entities_for_memory": ["medication name + dose for each medication"]
}

TEXT TO ANALYZE:
""",
}


# ── Mock responses for development ───────────────────────────────────────────

_MOCK_RESPONSES: dict[str, dict] = {
    "structured_lab": {
        "exam_name": "Urina I",
        "collection_date": None,
        "release_date": None,
        "sample_type": "urina",
        "findings": [
            {"name": "Leucócitos / campo", "value": "10", "unit": "/campo",
             "reference_range": "Até 5/campo", "flag": "high", "is_clinically_actionable": True},
            {"name": "Bacteriúria", "value": "Discreta", "unit": None,
             "reference_range": "Ausente / Discreta", "flag": "borderline", "is_clinically_actionable": True},
            {"name": "Nitrito", "value": "Ausente", "unit": None,
             "reference_range": "Ausente", "flag": "normal", "is_clinically_actionable": False},
            {"name": "Aspecto", "value": "Levemente turvo", "unit": None,
             "reference_range": "Límpido", "flag": "borderline", "is_clinically_actionable": True},
            {"name": "Glicose", "value": "Ausente", "unit": None,
             "reference_range": "Ausente", "flag": "normal", "is_clinically_actionable": False},
            {"name": "Proteínas", "value": "Ausente", "unit": None,
             "reference_range": "Ausente", "flag": "normal", "is_clinically_actionable": False},
        ],
        "summary": "Urina I com leucócitos acima do valor de referência (10/campo) e bacteriúria discreta, podendo sugerir processo infeccioso urinário. Recomenda-se correlação clínica.",
        "entities_for_memory": ["leucocitúria (10/campo, acima do normal)", "bacteriúria discreta", "aspecto levemente turvo"],
    },
    "imaging_narrative": {
        "modality": "CT",
        "body_region": "abdome e pelve",
        "indication": "dor abdominal",
        "findings": "Fígado com dimensões normais e contornos regulares. Baço, pâncreas e adrenais sem alterações significativas. Rins tópicos, com morfologia preservada.",
        "impression": "Exame dentro dos limites da normalidade para a faixa etária.",
        "recommendations": "Correlação clínica recomendada.",
        "urgency": "routine",
        "comparison_with_prior": None,
        "summary": "TC de abdome sem alterações significativas. Sem achados de urgência.",
        "entities_for_memory": ["TC abdome e pelve normal"],
    },
    "clinical_narrative": {
        "chief_complaint": "cefaleia há 3 dias",
        "symptoms": ["cefaleia", "fotofobia", "náusea"],
        "diagnoses": ["Enxaqueca sem aura"],
        "suspected_diagnoses": [],
        "allergies": ["Dipirona (reação anafilática)"],
        "medications": ["Sumatriptano 50mg", "Metoclopramida 10mg"],
        "conduct": "Prescrito sumatriptano para crises. Orientado evitar gatilhos.",
        "follow_up": "Retorno em 30 dias ou antes se piora",
        "specialties": ["Neurologia"],
        "summary": "Paciente com enxaqueca sem aura, cefaleia há 3 dias com fotofobia e náusea. Alergia a Dipirona.",
        "entities_for_memory": ["Enxaqueca sem aura", "Alergia a Dipirona (anafilaxia)", "uso de Sumatriptano 50mg"],
    },
    "medication_document": {
        "medications": [
            {"name": "Metformina", "dose": "850mg", "route": "oral",
             "frequency": "2x ao dia", "duration": "contínuo", "indication": "Diabetes tipo 2"},
            {"name": "Atorvastatina", "dose": "20mg", "route": "oral",
             "frequency": "1x ao dia (noite)", "duration": "contínuo", "indication": "dislipidemia"},
        ],
        "summary": "Prescrição com 2 medicamentos de uso contínuo: Metformina 850mg e Atorvastatina 20mg.",
        "entities_for_memory": ["Metformina 850mg 2x/dia", "Atorvastatina 20mg 1x/dia"],
    },
}


def _parse_json_response(raw: str) -> dict:
    """Extract JSON from LLM response, handling markdown fences."""
    # Strip markdown fences if present
    cleaned = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Try to find JSON object in the response
        m = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if m:
            return json.loads(m.group())
        raise


def extract_structured(clinical_text: str, document_family: str) -> dict:
    """
    Run family-specific LLM extraction on cleaned clinical text.
    Returns the structured data dict for the given family.
    """
    import os
    use_mock = os.getenv("USE_MOCK_AZURE", "true").lower() == "true"

    if use_mock or document_family == "unknown":
        return _MOCK_RESPONSES.get(document_family, {})

    prompt = _PROMPTS.get(document_family)
    if not prompt:
        return {}

    from services.azure.llm import generate_json
    full_prompt = prompt + "\n" + clinical_text

    try:
        raw = generate_json(system=_SYSTEM_BASE, user=full_prompt)
        return _parse_json_response(raw)
    except Exception as e:
        logger.exception(
            "extract_structured failed for family=%s: %s: %s",
            document_family,
            type(e).__name__,
            e,
        )
        return {}
