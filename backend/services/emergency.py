"""
Serviço de perfil de emergência.

Agrega dados das patient tables e textos de documentos para montar um EmergencyProfile
com as informações críticas: alergias, medicamentos em uso, condições ativas e tipo sanguíneo.

A página de emergência é pública (sem login), acessível via QR Code.
"""
import logging
import re
from datetime import datetime, timezone

from models.emergency import Allergy, EmergencyProfile, Medication
from services.supabase_store import _get_client

_log = logging.getLogger(__name__)

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

# Tracks whether the last call to _get_client succeeded (for None-check logic)
_client_query_failed = False


def build_emergency_profile(user_id: str) -> EmergencyProfile | None:
    """
    Constrói o perfil de emergência a partir das patient tables e documentos do usuário.

    Queries patient tables for structured conditions/medications/allergies (D-09).
    Soft-fail per D-12: table errors produce empty lists, not exceptions.
    Blood type still extracted via regex on document text (D-10).
    EmergencyProfile schema is unchanged (D-11).
    """
    # Query patient tables for structured data (D-09)
    # Soft-fail per D-12: table errors -> empty lists, not 500
    client_failed = False
    try:
        client = _get_client()
        cond_rows = client.table("patient_conditions").select("*").eq("user_id", user_id).eq("clinical_status", "active").execute()
        med_rows = client.table("patient_medications").select("*").eq("user_id", user_id).eq("status", "active").execute()
        allergy_rows = client.table("patient_allergies").select("*").eq("user_id", user_id).execute()
    except Exception as exc:
        _log.warning("emergency patient table query failed user_id=%s: %s", user_id, exc)
        client_failed = True
        cond_rows = med_rows = allergy_rows = type("R", (), {"data": []})()

    conditions = [r.get("normalized_condition", r.get("raw_condition", "")) for r in (cond_rows.data or [])]

    medications = []
    for r in (med_rows.data or []):
        name = r.get("normalized_medication", r.get("raw_medication", ""))
        dose = r.get("dose") or "ver prescrição"
        alert = None
        if any(drug in name.lower() for drug in _SURGICAL_RISK_DRUGS):
            alert = "risco cirúrgico — suspender 5 dias antes de procedimentos"
        medications.append(Medication(name=name, dose=dose, alert=alert))

    allergies = []
    for r in (allergy_rows.data or []):
        name = r.get("normalized_allergen", r.get("raw_allergen", ""))
        severity = "moderada"  # default; patient_allergies has reaction, not severity
        reaction = r.get("reaction", "")
        if reaction:
            for keyword, level in _SEVERITY_KEYWORDS.items():
                if keyword in (reaction or "").lower():
                    severity = level
                    break
        allergies.append(Allergy(name=name, severity=severity))

    # Blood type: still regex on document text — no patient table column (D-10)
    # Fetch full_text from documents for blood type only
    blood_type = None
    last_updated = datetime.now(timezone.utc)
    try:
        from services.document_store import list_by_user
        docs = list_by_user(user_id)
        if docs:
            full_text = "\n".join(doc.anonymized_text for doc in docs)
            blood_type = _extract_blood_type(full_text)
            last_updated = max(doc.upload_date for doc in docs)
    except Exception:
        pass  # Blood type unavailable — not critical

    # If patient table query succeeded but returned no data, check for documents
    if not client_failed and not conditions and not medications and not allergies and blood_type is None:
        try:
            from services.document_store import list_by_user as lbu
            if not lbu(user_id):
                return None
        except Exception:
            return None

    # If client_failed but we have absolutely nothing, still return profile with empty lists
    # (soft-fail: never raise, always return a usable — possibly empty — profile)
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
