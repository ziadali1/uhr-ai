"""
LLM — GPT-4o mini via Azure OpenAI.

Com USE_MOCK_AZURE=true, gera resposta simulada sem chamar a API.
A resposta mock usa as fontes recuperadas para parecer realista.
"""
import logging
import os
from collections.abc import Generator

logger = logging.getLogger(__name__)


def _use_mock() -> bool:
    return os.getenv("USE_MOCK_AZURE", "true").lower() == "true"


def _get_client():
    from openai import OpenAI

    base_url = os.environ["AZURE_OPENAI_BASE_URL"]
    api_key = os.environ["AZURE_OPENAI_API_KEY"]

    return OpenAI(
        base_url=base_url,
        api_key=api_key,
    )


def _get_chat_deployment() -> str:
    return os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4o-mini")


def chat_stream(
    system_prompt: str,
    messages: list[dict],
    sources: list[str],
) -> Generator[str, None, None]:
    """
    Envia mensagens ao Azure OpenAI e retorna um generator de chunks de texto (streaming).

    Args:
        system_prompt: prompt de sistema com contexto RAG injetado
        messages: histórico no formato [{"role": "user"|"assistant", "content": str}]
        sources: lista de nomes de documentos usados como contexto
    """
    if _use_mock():
        yield from _mock_stream(messages, sources)
        return

    client = _get_client()
    deployment = _get_chat_deployment()

    try:
        stream = client.chat.completions.create(
            model=deployment,
            messages=[
                {"role": "system", "content": system_prompt},
                *messages,
            ],
            max_tokens=1024,
            temperature=0.2,
            stream=True,
        )

        for chunk in stream:
            if not chunk.choices:
                continue

            delta = chunk.choices[0].delta
            if delta and getattr(delta, "content", None):
                yield delta.content

    except Exception:
        logger.exception("OpenAI streaming call failed")
        raise


def generate_json(system: str, user: str) -> str:
    """
    Single-turn call for structured JSON extraction.
    Returns raw response string (caller parses JSON).
    """
    if _use_mock():
        return "{}"

    if len(user) > 12000:
        user = user[:12000] + "\n\n[texto truncado]"

    client = _get_client()
    deployment = _get_chat_deployment()

    try:
        response = client.chat.completions.create(
            model=deployment,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            max_tokens=4096,
            temperature=0,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        return content if content else "{}"

    except Exception:
        logger.exception("OpenAI JSON call failed")
        raise


def _mock_stream(messages: list[dict], sources: list[str]) -> Generator[str, None, None]:
    """Resposta simulada que usa as fontes para parecer contextualizada."""
    import time

    last_user_msg = ""
    for m in reversed(messages):
        if m["role"] == "user":
            last_user_msg = m["content"]
            break

    source_ref = ""
    if sources:
        source_ref = f"\n\n📎 Fonte: {', '.join(sources)}"

    response = _build_mock_response(last_user_msg, sources)
    full_response = response + source_ref

    words = full_response.split(" ")
    for i, word in enumerate(words):
        yield word + (" " if i < len(words) - 1 else "")
        time.sleep(0.03)


def _build_mock_response(question: str, sources: list[str]) -> str:
    q = question.lower()
    has_docs = bool(sources)

    if not has_docs:
        return (
            "Não encontrei documentos médicos indexados para este usuário. "
            "Por favor, faça o upload de documentos na página de Documentos primeiro."
        )

    if any(w in q for w in ["heparina", "warfarina", "anticoagulante", "coagulação"]):
        return (
            "⚠️ Atenção: com base nos documentos analisados, o [PACIENTE] faz uso contínuo de "
            "Warfarina 5mg com INR alvo 2,0–3,0. A combinação com Heparina aumenta "
            "significativamente o risco hemorrágico e requer avaliação médica obrigatória "
            "antes de qualquer prescrição."
        )
    if any(w in q for w in ["alergi", "dipirona", "penicilina", "reação"]):
        return (
            "Com base nos documentos, o [PACIENTE] possui as seguintes alergias registradas:\n"
            "• Dipirona — reação anafilática severa\n"
            "• Penicilina — urticária\n\n"
            "Essas informações devem ser sempre comunicadas a qualquer profissional de saúde."
        )
    if any(w in q for w in ["medicamento", "remédio", "medicação", "usa", "toma"]):
        return (
            "Os medicamentos em uso registrados nos documentos são:\n"
            "• Metformina 850mg — 2x ao dia\n"
            "• Warfarina 5mg — 1x ao dia ⚠️ risco cirúrgico\n\n"
            "Lembre-se: qualquer alteração na medicação deve ser orientada pelo médico responsável."
        )
    if any(w in q for w in ["diagnóstico", "doença", "condição", "problema", "cid"]):
        return (
            "As condições ativas registradas nos documentos são:\n"
            "• Diabetes mellitus tipo 2 (CID E11)\n"
            "• Fibrilação atrial paroxística (CID I48)\n\n"
            "Estas informações são baseadas nos laudos enviados e não substituem avaliação médica atual."
        )
    if any(w in q for w in ["tipo sanguíneo", "sangue", "tipo"]):
        return "O tipo sanguíneo registrado nos documentos é **A positivo (A+)**."

    return (
        "Com base nos documentos analisados, encontrei informações relevantes para sua pergunta. "
        "Os registros indicam que o [PACIENTE] possui histórico de Diabetes tipo 2 e Fibrilação atrial, "
        "em uso de Metformina e Warfarina, com alergias a Dipirona e Penicilina. "
        "Para uma resposta mais precisa, reformule sua pergunta com mais detalhes."
    )
