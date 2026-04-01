"""
Document family classifier.

Classifies medical documents into one of 5 families using a hybrid strategy:
  1. Deterministic keyword rules (fast, no LLM cost) — used when confidence is high
  2. LLM fallback (Claude) — used when regex signals are weak or ambiguous

Families:
  structured_lab       — blood tests, urinalysis, hormones, biochemistry
  imaging_narrative    — CT, MRI, ultrasound, X-ray, mammography, pathology
  clinical_narrative   — visit notes, discharge summaries, referrals, emergency notes
  medication_document  — prescriptions, medication lists, dosage plans
  unknown              — last-resort fallback when LLM also cannot determine family

Threshold logic:
  best_score >= 2   → use regex result directly (high confidence)
  best_score == 1   → regex suggests a family, but LLM confirms or overrides
  best_score == 0   → no regex signal at all, LLM decides
"""

import json
import os
import re

# ── Confidence threshold below which LLM is consulted ────────────────────────

_LLM_THRESHOLD = 2   # if best regex score < this, call LLM

# ── Keyword signal groups ─────────────────────────────────────────────────────

_LAB_STRONG = [
    r"\bvalor\s+de\s+refer[eê]ncia\b",
    r"\bvalores?\s+de\s+refer[eê]ncia\b",
    r"\bvr\b",
    r"\bresultado\b.{0,40}\b(mg|g|dl|mmol|u/l|ug|ng|pg|meq|ui|nm|mm|cm|%)\b",
    r"\bhem[oó]grama\b",
    r"\bbioquímica\b",
    r"\burocultura\b",
    r"\burina\s+i\b",
    r"\burinálise\b",
    r"\bcreatinina\b",
    r"\bglicose\b",
    r"\bhemoglobina\b",
    r"\bleuc[oó]citos\b",
    r"\bplaquetas\b",
    r"\btsh\b",
    r"\bvitamina\s+d\b",
    r"\bcolesterol\b",
    r"\btriglicer[ií]deos\b",
    r"\bpcr\b",
    r"\bvhs\b",
    r"\bhba1c\b",
    r"\bneutrófilos\b",
    r"\bbasófilos\b",
    r"\beosinas?\b",
    r"\bmonócitos\b",
    r"\blinfócitos\b",
]

_IMAGING_STRONG = [
    r"\btomografia\b",
    r"\bressonância\s+magn[eé]tica\b",
    r"\bultrassonografia\b",
    r"\bradiografia\b",
    r"\bmamografia\b",
    r"\blaudo\s+(?:m[eé]dico|radiol[oó]gico|anat[oó]mo)\b",
    r"\bimpress[aã]o\s+diagn[oó]stica\b",
    r"\bopacidade\b",
    r"\bparênquima\b",
    r"\beco\s+(?:abdominal|pélvico|card[ií]aco)\b",
    r"\bsinais?\s+de\b.{0,60}\b(hérnia|edema|efus[aã]o|les[aã]o|n[oó]dulo|massa)\b",
    r"\baspecto\s+radiol[oó]gico\b",
    r"\bsem\s+altera[çc][õo]es\s+significativas\b",
    r"\bcaix[aã]\s+tor[aá]cica\b",
    r"\bpl[ae]ura\b",
    r"\bmiocard[ií]o\b",
    r"\bbiópsia\b",
    r"\bhistopatol[oó]gico\b",
    r"\banat[oó]mo.{0,10}patol[oó]gico\b",
    r"\bfragmentos?\s+de\s+tecido\b",
]

_CLINICAL_STRONG = [
    r"\bqueixa\s+principal\b",
    r"\bprontu[aá]rio\b",
    r"\balta\s+hospitalar\b",
    r"\bencaminhamento\b",
    r"\breceituário\b",
    r"\banamnese\b",
    r"\bexame\s+f[ií]sico\b",
    r"\bhip[oó]tese\s+diagn[oó]stica\b",
    r"\bconduta\b",
    r"\bplano\s+terap[eê]utico\b",
    r"\bpressão\s+arterial\b",
    r"\bsaturaç[aã]o\b",
    r"\bfrequência\s+card[ií]aca\b",
    r"\bhistória\s+cl[ií]nica\b",
    r"\bdiagnósticos?\b.{0,30}\b(definido|confirm|ativo)\b",
    r"\bevolução\s+cl[ií]nica\b",
    r"\bprogresso\s+cl[ií]nico\b",
    r"\bnota\s+de\s+(?:atendimento|alta|evolu[çc][aã]o)\b",
]

_MEDICATION_STRONG = [
    r"\breceita\s+m[eé]dica\b",
    r"\bprescriç[aã]o\b",
    r"\bprescrição\s+m[eé]dica\b",
    r"\buso\s+cont[ií]nuo\b",
    r"\bposologia\b",
    r"\bvia\s+oral\b",
    r"\bcomprimido\b.{0,60}\b(tomar|administrar|usar)\b",
    r"\b\d+\s*mg\b.{0,30}\b(ao\s+dia|x\s+ao\s+dia|por\s+dia)\b",
]

_VALID_FAMILIES = {
    "structured_lab", "imaging_narrative", "clinical_narrative",
    "medication_document", "unknown",
}


def _score(text: str, patterns: list[str]) -> int:
    tl = text.lower()
    return sum(1 for p in patterns if re.search(p, tl))


_LLM_SYSTEM = (
    "You are a medical document classifier. "
    "Classify the document into exactly ONE of these families:\n"
    "- structured_lab: blood tests, urinalysis, hormones, biochemistry, microbiology tables\n"
    "- imaging_narrative: CT, MRI, ultrasound, X-ray, mammography, pathology/histology reports\n"
    "- clinical_narrative: visit notes, discharge summaries, referrals, progress notes, emergency notes\n"
    "- medication_document: prescriptions, medication lists, dosage plans\n"
    "- unknown: cannot determine from the text\n\n"
    "Respond ONLY with valid JSON, no explanation:\n"
    '{"family": "<family>", "confidence": <0.0-1.0>, "reason": "<one sentence>"}'
)


def _llm_classify(text: str) -> tuple[str, float]:
    """Call Claude to classify when regex confidence is insufficient."""
    use_mock = os.getenv("USE_MOCK_AZURE", "true").lower() == "true"
    if use_mock:
        # In mock mode, default to unknown rather than making a bad guess
        return "unknown", 0.3

    try:
        from services.azure.llm import generate_json

        # Send first 2000 chars — enough for classification, cheap to call
        snippet = text[:2000]
        raw = generate_json(
            system=_LLM_SYSTEM,
            user=f"Classify this medical document:\n\n{snippet}",
        )

        parsed = json.loads(raw.strip())
        family = parsed.get("family", "unknown")
        confidence = float(parsed.get("confidence", 0.5))

        if family not in _VALID_FAMILIES:
            family = "unknown"

        return family, round(confidence, 2)

    except Exception:
        return "unknown", 0.2


def classify(text: str) -> tuple[str, float]:
    """
    Returns (document_family, confidence_0_to_1).

    Strategy:
      - If regex signals are strong (score >= LLM_THRESHOLD): trust regex result
      - Otherwise: call LLM for semantic classification
      - If LLM also fails: return unknown
    """
    scores = {
        "structured_lab": _score(text, _LAB_STRONG),
        "imaging_narrative": _score(text, _IMAGING_STRONG),
        "clinical_narrative": _score(text, _CLINICAL_STRONG),
        "medication_document": _score(text, _MEDICATION_STRONG),
    }

    best_family = max(scores, key=lambda k: scores[k])
    best_score = scores[best_family]

    # High-confidence regex path
    if best_score >= _LLM_THRESHOLD:
        total_patterns = {
            "structured_lab": len(_LAB_STRONG),
            "imaging_narrative": len(_IMAGING_STRONG),
            "clinical_narrative": len(_CLINICAL_STRONG),
            "medication_document": len(_MEDICATION_STRONG),
        }
        confidence = min(best_score / max(total_patterns[best_family] * 0.3, 1), 1.0)
        return best_family, round(confidence, 2)

    # Low/no regex signal → LLM decides
    return _llm_classify(text)
