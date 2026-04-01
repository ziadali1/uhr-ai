"""
LLM — Claude via Azure AI Foundry.

Com USE_MOCK_AZURE=true, gera resposta simulada sem chamar a API.
A resposta mock usa as fontes recuperadas para parecer realista.
"""
import os
from collections.abc import Generator


def _use_mock() -> bool:
    return os.getenv("USE_MOCK_AZURE", "true").lower() == "true"


def chat_stream(
    system_prompt: str,
    messages: list[dict],
    sources: list[str],
) -> Generator[str, None, None]:
    """
    Envia mensagens ao Claude e retorna um generator de chunks de texto (streaming).

    Args:
        system_prompt: prompt de sistema com contexto RAG injetado
        messages: histórico no formato [{"role": "user"|"assistant", "content": str}]
        sources: lista de nomes de documentos usados como contexto
    """
    if _use_mock():
        yield from _mock_stream(messages, sources)
        return

    import anthropic

    client = anthropic.Anthropic(
        base_url=os.environ["ANTHROPIC_BASE_URL"],
        api_key=os.environ["ANTHROPIC_API_KEY"],
        default_headers={"api-key": os.environ["ANTHROPIC_API_KEY"]},
    )

    with client.messages.stream(
        model="claude-sonnet-4-5",
        max_tokens=1024,
        system=system_prompt,
        messages=messages,
    ) as stream:
        for text in stream.text_stream:
            yield text


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

    # Respostas mock por palavras-chave
    response = _build_mock_response(last_user_msg, sources)
    full_response = response + source_ref

    # Simula streaming palavra por palavra
    words = full_response.split(" ")
    for i, word in enumerate(words):
        yield word + (" " if i < len(words) - 1 else "")
        time.sleep(0.03)


def generate_json(system: str, user: str) -> str:
    """
    Single-turn Claude call for structured JSON extraction.
    Returns raw response string (caller parses JSON).
    """
    if _use_mock():
        return "{}"

    if len(user) > 12000:
        user = user[:12000] + "\n\n[texto truncado]"

    import anthropic

    client = anthropic.Anthropic(
        base_url=os.environ["ANTHROPIC_BASE_URL"],
        api_key=os.environ["ANTHROPIC_API_KEY"],
        default_headers={"api-key": os.environ["ANTHROPIC_API_KEY"]},
    )
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=4096,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return response.content[0].text


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
        f"Com base nos documentos analisados, encontrei informações relevantes para sua pergunta. "
        f"Os registros indicam que o [PACIENTE] possui histórico de Diabetes tipo 2 e Fibrilação atrial, "
        f"em uso de Metformina e Warfarina, com alergias a Dipirona e Penicilina. "
        f"Para uma resposta mais precisa, reformule sua pergunta com mais detalhes."
    )
