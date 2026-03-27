"""
Serviço de perfil de emergência.

Agrega entidades de todos os documentos do usuário e monta um EmergencyProfile
com as informações críticas: alergias, medicamentos em uso, condições ativas e tipo sanguíneo.

A página de emergência é pública (sem login), acessível via QR Code.
"""
import re
from datetime import datetime, timezone

from models.emergency import Allergy, EmergencyProfile, Medication
from models.document import ExtractedEntity
from services.document_store import list_by_user

# Padrão para detectar tipo sanguíneo no texto
_BLOOD_TYPE_RE = re.compile(
    r"\b(A|B|AB|O)\s*[\+\-](positivo|negativo)?\b",
    re.IGNORECASE,
)

# Medicamentos que exigem alerta cirúrgico
_SURGICAL_RISK_DRUGS = {"warfarin", "warfarina", "heparin", "heparina", "rivaroxaban", "apixaban"}

# Mapeamento de severidade baseado em palavras-chave no texto bruto
_SEVERITY_KEYWORDS = {
    "severa": "severa",
    "anafilática": "severa",
    "anafilaxia": "severa",
    "grave": "severa",
    "moderada": "moderada",
    "urticária": "moderada",
    "leve": "leve",
}


def build_emergency_profile(user_id: str) -> EmergencyProfile | None:
    """
    Constrói o perfil de emergência a partir dos documentos do usuário.
    Retorna None se não houver documentos.
    """
    docs = list_by_user(user_id)
    if not docs:
        return None

    all_entities: list[ExtractedEntity] = []
    full_text = ""
    last_updated = datetime.min.replace(tzinfo=timezone.utc)

    for doc in docs:
        all_entities.extend(doc.medical_entities)
        full_text += "\n" + doc.anonymized_text
        if doc.upload_date > last_updated:
            last_updated = doc.upload_date

    blood_type = _extract_blood_type(full_text)
    allergies = _build_allergies(all_entities, full_text)
    medications = _build_medications(all_entities)
    conditions = _build_conditions(all_entities)

    return EmergencyProfile(
        user_id=user_id,
        blood_type=blood_type,
        allergies=allergies,
        active_medications=medications,
        active_conditions=conditions,
        last_updated=last_updated,
    )


def _extract_blood_type(text: str) -> str | None:
    match = _BLOOD_TYPE_RE.search(text)
    if not match:
        return None
    raw = match.group(0).strip()
    # Normaliza para formato curto: "A positivo" → "A+"
    raw_lower = raw.lower()
    sign = "+" if "positivo" in raw_lower or "+" in raw else "-"
    group = re.match(r"(AB|A|B|O)", raw, re.IGNORECASE)
    if group:
        return f"{group.group(1).upper()}{sign}"
    return raw


def _build_allergies(entities: list[ExtractedEntity], full_text: str) -> list[Allergy]:
    seen: set[str] = set()
    allergies: list[Allergy] = []
    text_lower = full_text.lower()

    for e in entities:
        if e.category != "AllergyEntity":
            continue
        name = e.normalized_text or e.text
        if name.lower() in seen:
            continue
        seen.add(name.lower())

        # Tenta inferir severidade pelo texto ao redor
        severity = "moderada"
        for keyword, level in _SEVERITY_KEYWORDS.items():
            if keyword in text_lower:
                severity = level
                break

        allergies.append(Allergy(name=name, severity=severity))

    return allergies


def _build_medications(entities: list[ExtractedEntity]) -> list[Medication]:
    seen: set[str] = set()
    medications: list[Medication] = []

    for e in entities:
        if e.category != "MedicationName":
            continue
        name = e.normalized_text or e.text
        if name.lower() in seen:
            continue
        seen.add(name.lower())

        alert = None
        if any(drug in name.lower() for drug in _SURGICAL_RISK_DRUGS):
            alert = "risco cirúrgico — suspender 5 dias antes de procedimentos"

        # Tenta extrair dose do texto original (ex: "Metformina 850mg")
        dose_match = re.search(r"(\d+\s*mg|\d+\s*mcg|\d+\s*ml)", e.text, re.IGNORECASE)
        dose = dose_match.group(0) if dose_match else "ver prescrição"

        medications.append(Medication(name=name, dose=dose, alert=alert))

    return medications


def _build_conditions(entities: list[ExtractedEntity]) -> list[str]:
    seen: set[str] = set()
    conditions: list[str] = []
    for e in entities:
        if e.category != "Diagnosis":
            continue
        label = e.normalized_text or e.text
        if label.lower() not in seen:
            seen.add(label.lower())
            conditions.append(label)
    return conditions
