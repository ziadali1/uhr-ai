"""
RAG Retriever — routes query, fetches SQL + search results, assembles context for Claude.

Refactored in Phase 5 (RETRIEVE-04, RETRIEVE-05):
  - Calls route_query() to classify intent before retrieval
  - Executes SQL steps for structured patient data (sql_only, mixed)
  - Calls hybrid search for narrative queries (search_only, mixed)
  - Assembles structured clinical context blocks via assemble_chat_block()
  - Preserves build_context_prompt(question, user_id) -> tuple[str, list[str]] signature
"""
from services.azure.search import search, SearchResult
from services.azure.embeddings import generate_embedding
from services.rag.router import (
    route_query,
    execute_sql_steps,
    format_sql_block,
    assemble_chat_block,
    build_patient_summary,
)

SYSTEM_PROMPT = """Você é um assistente clínico de suporte ao paciente. Analisa o histórico médico completo e responde com raciocínio clínico, não apenas com lookup literal de dados.

Regras obrigatórias:
- Use o PERFIL CLÍNICO DO PACIENTE como âncora — ele contém os dados estruturados verificados.
- Interprete valores em contexto clínico: mencione valores de referência quando relevante, sinalize alterações, identifique padrões.
- Sintetize informações de múltiplas fontes (perfil + exames detalhados + documentos narrativos) numa resposta coerente.
- Se o paciente pergunta sobre algo que não está nos dados, diga claramente o que não foi encontrado E o que está disponível que pode ser relevante.
- Nunca invente dados clínicos ou valores laboratoriais.
- Nunca emita diagnósticos definitivos — oriente sempre a confirmar com o médico responsável.
- Cite a fonte ao mencionar informações de documentos narrativos.
- Responda sempre em português do Brasil."""


def build_context_prompt(question: str, user_id: str) -> tuple[str, list[str]]:
    """
    Build clinical context for the LLM: compact patient summary (always) +
    targeted SQL results + narrative search results (intent-driven).

    Signature preserved: (question: str, user_id: str) -> (system_prompt_with_context, sources).
    api/chat.py requires no changes.
    """
    # Step 1: build compact patient summary — anchors both routing and the final context
    patient_summary = build_patient_summary(user_id)

    # Step 2: classify intent using the summary as context (router uses exact names from profile)
    routing = route_query(question, user_id, patient_summary=patient_summary)

    # Step 3: targeted SQL for structured data (sql_only or mixed)
    sql_block = ""
    if routing.intent in ("sql_only", "mixed") and routing.sql_steps:
        sql_results = execute_sql_steps(routing.sql_steps, user_id)
        sql_block = format_sql_block(sql_results)

    # Step 4: hybrid search for narrative documents (search_only or mixed)
    # Reduce top_k 3->2 when structured data is already present (context budget)
    search_results: list[SearchResult] = []
    sources: list[str] = []
    if routing.intent in ("search_only", "mixed"):
        top_k = 2 if (patient_summary or sql_block) else 3
        search_query = routing.search_queries[0] if routing.search_queries else question
        query_vector = generate_embedding(search_query)
        search_results = search(search_query, user_id, top_k=top_k, query_vector=query_vector)
        for r in search_results:
            if r.source_name not in sources:
                sources.append(r.source_name)

    if routing.intent == "sql_only" and not sources:
        sources = ["dados estruturados do paciente"]

    # Step 5: assemble context — summary always first, then targeted SQL, then narrative docs
    context_sections: list[str] = []

    if patient_summary:
        context_sections.append(patient_summary)

    if sql_block:
        context_sections.append(sql_block)

    if search_results:
        doc_parts: list[str] = []
        for r in search_results:
            block = assemble_chat_block(
                doc_id=r.doc_id,
                source_name=r.source_name,
                excerpt=r.excerpt,
                collection_date=None,
            )
            doc_parts.append(block)
        docs_section = (
            "=== DOCUMENTOS DE SUPORTE ===\n\n"
            + "\n\n---\n\n".join(doc_parts)
            + "\n\n=== FIM DOS DOCUMENTOS ==="
        )
        context_sections.append(docs_section)

    if not context_sections:
        return f"{SYSTEM_PROMPT}\n\nNenhum dado médico encontrado para este usuário.", []

    full_context = "\n\n".join(context_sections)
    full_system = f"{SYSTEM_PROMPT}\n\n{full_context}"

    return full_system, sources
