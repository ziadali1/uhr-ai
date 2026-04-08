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
)

SYSTEM_PROMPT = """Você é um assistente médico de suporte ao paciente.
Seu papel é responder perguntas com base EXCLUSIVAMENTE nas informações fornecidas abaixo.
Regras obrigatórias:
- Nunca invente informações que não estejam nos dados fornecidos.
- Sempre cite a fonte (nome do documento) ao mencionar uma informação de documento.
- Se a informação não estiver disponível, diga claramente que não encontrou.
- Nunca emita diagnósticos. Se perguntado, lembre que suas respostas são informativas e não substituem avaliação médica.
- Responda sempre em português do Brasil.
- Os dados estruturados do paciente (seção === DADOS ESTRUTURADOS DO PACIENTE ===) representam fatos verificados extraídos dos registros médicos. Trate-os como fonte primária de verdade.
- Os documentos de suporte (seção === DOCUMENTOS DE SUPORTE ===) fornecem contexto narrativo e clínico adicional. Use-os como evidência de apoio.
- Ao responder, sintetize as informações de ambas as seções quando disponíveis."""


def build_context_prompt(question: str, user_id: str) -> tuple[str, list[str]]:
    """
    Route query, fetch SQL + search results, assemble structured context for Claude.

    Signature preserved: (question: str, user_id: str) -> (system_prompt_with_context, sources).
    api/chat.py requires no changes.
    """
    # Step 1: classify intent, extract entities, resolve temporal references (RETRIEVE-04)
    routing = route_query(question, user_id)

    # Step 2: execute SQL steps for structured patient data (sql_only or mixed)
    sql_block = ""
    if routing.intent in ("sql_only", "mixed") and routing.sql_steps:
        sql_results = execute_sql_steps(routing.sql_steps, user_id)
        sql_block = format_sql_block(sql_results)

    # Step 3: hybrid search for narrative queries (search_only or mixed)
    # Reduce top_k 3->2 when SQL block has data (D-14 context budget)
    search_results: list[SearchResult] = []
    sources: list[str] = []
    if routing.intent in ("search_only", "mixed"):
        top_k = 2 if sql_block else 3
        # Use first search_query if available, else fall back to original question
        search_query = routing.search_queries[0] if routing.search_queries else question
        query_vector = generate_embedding(search_query)
        search_results = search(search_query, user_id, top_k=top_k, query_vector=query_vector)
        for r in search_results:
            if r.source_name not in sources:
                sources.append(r.source_name)

    # sql_only: no search — sources come from SQL table labels
    if routing.intent == "sql_only" and not sources:
        sources = ["dados estruturados do paciente"]

    # Step 4: assemble context sections (D-12/D-13 ordering: SQL first, docs second)
    context_sections: list[str] = []

    if sql_block:
        context_sections.append(sql_block)

    if search_results:
        doc_parts: list[str] = []
        for r in search_results:
            block = assemble_chat_block(
                doc_id=r.doc_id,
                source_name=r.source_name,
                excerpt=r.excerpt,
                collection_date=None,  # not available on SearchResult; assembler uses "data desconhecida"
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
