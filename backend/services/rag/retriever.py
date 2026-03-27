"""
RAG Retriever — busca documentos relevantes e monta o prompt para o LLM.
"""
from services.azure.search import search, SearchResult

SYSTEM_PROMPT = """Você é um assistente médico de suporte ao paciente.
Seu papel é responder perguntas com base EXCLUSIVAMENTE nos documentos médicos fornecidos abaixo.
Regras obrigatórias:
- Nunca invente informações que não estejam nos documentos.
- Sempre cite a fonte (nome do documento) ao mencionar uma informação.
- Se a informação não estiver nos documentos, diga claramente que não encontrou.
- Nunca emita diagnósticos. Se perguntado, lembre que suas respostas são informativas e não substituem avaliação médica.
- Responda sempre em português do Brasil."""


def build_context_prompt(question: str, user_id: str) -> tuple[str, list[str]]:
    """
    Busca documentos relevantes e retorna (system_prompt_com_contexto, fontes).

    Returns:
        system_prompt: prompt de sistema com contexto do paciente injetado
        sources: lista de nomes de documentos usados como fonte
    """
    results: list[SearchResult] = search(question, user_id, top_k=3)

    if not results:
        context_block = "Nenhum documento médico encontrado para este usuário."
        return f"{SYSTEM_PROMPT}\n\n{context_block}", []

    context_parts = []
    sources = []
    for r in results:
        context_parts.append(
            f"[Fonte: {r.source_name}]\n{r.excerpt}"
        )
        if r.source_name not in sources:
            sources.append(r.source_name)

    context_block = "\n\n---\n\n".join(context_parts)
    full_system = (
        f"{SYSTEM_PROMPT}\n\n"
        f"=== DOCUMENTOS DO PACIENTE ===\n\n"
        f"{context_block}\n\n"
        f"=== FIM DOS DOCUMENTOS ==="
    )

    return full_system, sources
