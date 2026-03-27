"""
Serviço de análise do histórico médico do paciente.

Fluxo:
  busca todos os documentos do usuário → agrega entidades por categoria
  → monta prompt de análise → LLM gera resumo, hipóteses e especialidades sugeridas
"""
import os
from models.analysis import AnalysisResult, SuggestedSpecialty
from models.document import ExtractedEntity
from services.document_store import list_by_user


def _use_mock() -> bool:
    return os.getenv("USE_MOCK_AZURE", "true").lower() == "true"


def analyze_patient(user_id: str) -> AnalysisResult | None:
    """
    Analisa o histórico completo do paciente e retorna resumo estruturado.
    Retorna None se não houver documentos para o usuário.
    """
    docs = list_by_user(user_id)
    if not docs:
        return None

    # Agrega entidades de todos os documentos por categoria
    all_entities: list[ExtractedEntity] = []
    for doc in docs:
        all_entities.extend(doc.medical_entities)

    diagnoses = _unique_texts(all_entities, "Diagnosis")
    medications = _unique_texts(all_entities, "MedicationName")
    allergies = _unique_texts(all_entities, "AllergyEntity")
    symptoms = _unique_texts(all_entities, "Symptom")

    if _use_mock():
        return _mock_analysis(user_id, diagnoses, medications, allergies, symptoms, len(docs))

    # Produção: chama o LLM para gerar resumo e especialidades
    return _llm_analysis(user_id, diagnoses, medications, allergies, symptoms, len(docs))


def _unique_texts(entities: list[ExtractedEntity], category: str) -> list[str]:
    """Retorna textos únicos de entidades de uma categoria, priorizando normalized_text."""
    seen: set[str] = set()
    result: list[str] = []
    for e in entities:
        if e.category != category:
            continue
        label = e.normalized_text or e.text
        if label.lower() not in seen:
            seen.add(label.lower())
            result.append(label)
    return result


def _mock_analysis(
    user_id: str,
    diagnoses: list[str],
    medications: list[str],
    allergies: list[str],
    symptoms: list[str],
    doc_count: int,
) -> AnalysisResult:
    """Gera análise mockada a partir das entidades agregadas dos documentos."""
    has_anticoagulant = any("warfarin" in m.lower() or "warfarina" in m.lower() for m in medications)
    has_diabetes = any("diabetes" in d.lower() for d in diagnoses)
    has_afib = any("atrial" in d.lower() or "fibrilação" in d.lower() for d in diagnoses)

    # Resumo do caso
    diag_str = ", ".join(diagnoses) if diagnoses else "nenhum diagnóstico registrado"
    med_str = ", ".join(medications) if medications else "nenhum medicamento registrado"
    summary = (
        f"Paciente com histórico médico composto por {doc_count} documento(s). "
        f"Condições ativas identificadas: {diag_str}. "
        f"Medicamentos em uso: {med_str}."
    )
    if has_anticoagulant:
        summary += " Em uso de anticoagulante — atenção a procedimentos cirúrgicos."
    if allergies:
        summary += f" Alergias registradas: {', '.join(allergies)}."

    # Especialidades sugeridas com base nos diagnósticos
    specialties: list[SuggestedSpecialty] = []
    if has_diabetes:
        specialties.append(SuggestedSpecialty(
            specialty="Endocrinologia",
            reason="Presença de Diabetes mellitus tipo 2 requer acompanhamento especializado.",
        ))
    if has_afib or has_anticoagulant:
        specialties.append(SuggestedSpecialty(
            specialty="Cardiologia",
            reason="Fibrilação atrial e uso de anticoagulante (Warfarina) indicam acompanhamento cardiológico.",
        ))
    if allergies:
        specialties.append(SuggestedSpecialty(
            specialty="Alergologia/Imunologia",
            reason=f"Alergias registradas ({', '.join(allergies)}) devem ser avaliadas por especialista.",
        ))
    if not specialties:
        specialties.append(SuggestedSpecialty(
            specialty="Clínica Geral",
            reason="Recomenda-se avaliação com médico clínico geral para triagem inicial.",
        ))

    return AnalysisResult(
        user_id=user_id,
        case_summary=summary,
        diagnoses=diagnoses,
        active_medications=medications,
        allergies=allergies,
        suggested_specialties=specialties,
        document_count=doc_count,
    )


def _llm_analysis(
    user_id: str,
    diagnoses: list[str],
    medications: list[str],
    allergies: list[str],
    symptoms: list[str],
    doc_count: int,
) -> AnalysisResult:
    """Gera análise via LLM (Claude). Implementado quando USE_MOCK_AZURE=false."""
    # TODO: montar prompt estruturado e chamar services/azure/llm.py
    # O LLM retorna JSON com case_summary, suggested_specialties etc.
    raise NotImplementedError("Análise via LLM será ativada com credenciais Azure configuradas.")
