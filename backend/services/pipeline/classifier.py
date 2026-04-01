"""
Document family classifier.

Classifies medical documents into one of 5 families using a hybrid strategy:
  1. Deterministic keyword rules (fast, no LLM cost)
  2. LLM fallback for ambiguous documents

Families:
  structured_lab       — blood tests, urinalysis, hormones, biochemistry
  imaging_narrative    — CT, MRI, ultrasound, X-ray, mammography
  clinical_narrative   — visit notes, discharge summaries, referrals
  medication_document  — prescriptions, medication lists
  unknown              — fallback when confidence is low
"""

import re

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
    r"\blaudo\s+m[eé]dico\b",
    r"\blaudo\s+radiol[oó]gico\b",
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


def _score(text: str, patterns: list[str]) -> int:
    tl = text.lower()
    return sum(1 for p in patterns if re.search(p, tl))


def classify(text: str) -> tuple[str, float]:
    """
    Returns (document_family, confidence_0_to_1).
    Confidence is approximate — based on signal count vs total patterns.
    """
    scores = {
        "structured_lab": _score(text, _LAB_STRONG),
        "imaging_narrative": _score(text, _IMAGING_STRONG),
        "clinical_narrative": _score(text, _CLINICAL_STRONG),
        "medication_document": _score(text, _MEDICATION_STRONG),
    }

    best_family = max(scores, key=lambda k: scores[k])
    best_score = scores[best_family]

    if best_score == 0:
        return "unknown", 0.0

    # Confidence: ratio of matched signals to total patterns for that family
    total_patterns = {
        "structured_lab": len(_LAB_STRONG),
        "imaging_narrative": len(_IMAGING_STRONG),
        "clinical_narrative": len(_CLINICAL_STRONG),
        "medication_document": len(_MEDICATION_STRONG),
    }
    confidence = min(best_score / max(total_patterns[best_family] * 0.3, 1), 1.0)

    # Require at least 2 signals for high confidence
    if best_score < 2:
        confidence = min(confidence, 0.55)

    return best_family, round(confidence, 2)
